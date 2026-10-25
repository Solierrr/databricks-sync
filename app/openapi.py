from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.models import ProblemDetail

PROBLEM_REF = "#/components/schemas/ProblemDetail"


def build_openapi(app: FastAPI, include_internal: bool) -> dict:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        servers=app.servers,
        contact=app.contact,
        license_info=app.license_info,
    )
    schema["security"] = [{"bearerAuth": []}]
    schemas = schema.setdefault("components", {}).setdefault("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)
    problem_schema = ProblemDetail.model_json_schema(ref_template="#/components/schemas/{model}")
    schemas.update(problem_schema.pop("$defs", {}))
    schemas["ProblemDetail"] = problem_schema
    for path in schema["paths"].values():
        for operation in path.values():
            responses = operation.setdefault("responses", {})
            responses.setdefault("500", {"description": "Erro interno inesperado"})
            if responses.get("422", {}).get("description") == "Validation Error":
                responses["422"]["description"] = "Parâmetro inválido"
            for code, response in responses.items():
                if code.startswith(("4", "5")):
                    response["content"] = {"application/problem+json": {"schema": {"$ref": PROBLEM_REF}}}
    if not include_internal:
        schema["paths"] = {p: v for p, v in schema["paths"].items() if not p.startswith("/internal/")}
        used = {tag for path in schema["paths"].values() for operation in path.values() for tag in operation.get("tags", [])}
        schema["tags"] = [tag for tag in schema.get("tags", []) if tag["name"] in used]
    return schema


def install_openapi(app: FastAPI) -> None:
    def public_openapi() -> dict:
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi(app, include_internal=False)
        return app.openapi_schema

    app.openapi = public_openapi
