import logging

logger = logging.getLogger(__name__)

def exclude_docs_views(endpoints):
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"Processing endpoints in exclude_docs_views: {len(endpoints)} endpoints")

    filtered = []
    for path, path_regex, method, callback in endpoints:
        callback_module = callback.__module__
        callback_name = callback.__qualname__

        if "apidocs.views" in callback_module:
            logger.info(f"Excluding doc view: {callback_module}.{callback_name} -> {method} {path}")
            continue

        filtered.append((path, path_regex, method, callback))

    logger.info(f"Filtered to {len(filtered)} endpoints")
    return filtered


def remove_none_auth(result, **kwargs):
    """
    Cleans up redundant or empty security schemes in the generated OpenAPI spec.
    Ensures that only valid schemes (like jwtAuth) remain and removes any duplicates or invalid schemes.
    """
    import logging
    logger = logging.getLogger(__name__)

    for _path, methods in result.get("paths", {}).items():
        for _method, operation in methods.items():
            security = operation.get("security")
            if not security:
                continue

            # Remove any duplicate or invalid schemes like jwtAuthjwtAuth
            cleaned_security = []
            seen_schemes = set()

            for scheme in security:
                # Check if the scheme is valid and has not been seen before
                if scheme and isinstance(scheme, dict):
                    scheme_name = list(scheme.keys())[0]
                    if scheme_name == "jwtAuth" and scheme_name not in seen_schemes:
                        cleaned_security.append(scheme)
                        seen_schemes.add(scheme_name)

            # If any valid schemes remain, update the operation security
            if cleaned_security:
                operation["security"] = cleaned_security
            else:
                operation.pop("security", None)

            logger.debug(f"Cleaned security for operation {operation.get('operationId')}: {cleaned_security}")

    return result


def beautify_operation_ids(result, **kwargs):
    """
    Convert auto-generated operationIds like:
      users_crud_departments_list
    into human-readable summaries:
      List Departments
    """
    paths = result.get("paths", {})

    for _path, methods in paths.items():
        for _method, operation in methods.items():
            if not isinstance(operation, dict):
                continue

            operation_id = operation.get("operationId")
            summary = operation.get("summary")

            # Skip if developer explicitly set summary
            if summary:
                continue

            if not operation_id:
                continue

            tokens = operation_id.split("_")

            action_map = {
                "list": "List",
                "retrieve": "Retrieve",
                "create": "Create",
                "update": "Update",
                "partial": "Partial Update",
                "destroy": "Delete",
                "delete": "Delete",
            }

            action = tokens[-1]
            action_label = action_map.get(action)
            if not action_label:
                continue

            # Best heuristic: last noun before action
            resource = tokens[-2].replace("-", " ").title() if len(tokens) >= 2 else "Resource"

            operation["summary"] = f"{action_label} {resource}"

    return result


