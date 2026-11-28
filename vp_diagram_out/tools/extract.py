#!/usr/bin/env python3
"""Static extractor and VP prompt generator for Veriq services.

This is intentionally a source scanner, not an application test. It combines
Python AST with narrowly scoped regex scans of source text. Results are
traceable candidates; review.md records the assumptions used by the generator.
"""
from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "vp_diagram_out"
SERVICES = ["authentication", "content", "cloud", "notification", "testing", "worker", "ai"]
TECH = re.compile(r"(^sessions$|tokens?$|audit|outbox|checkpoint|platform_state|worker_jobs|admin_operations|system_configs|service_identities|secret_references|ai_providers|ai_models|cache|index|queue|job$|dead_letter|embedding|vector|receipts?$|source_facts$|agent_traces)", re.I)
EXTERNAL_REFERENCE_SERVICES={"user":"authentication","owner_user":"authentication","target_user":"authentication","actor":"authentication","created_by":"authentication","updated_by":"authentication","deleted_by":"authentication","requester":"authentication","reviewer":"authentication","project":"testing","test_case":"testing","test_plan":"testing","test_run":"testing","test_result":"testing","requirement":"testing","defect":"testing","release":"testing","document":"content","source_document":"content","folder":"content","storage_item":"cloud","file":"cloud","notification":"notification","ai_run":"ai","ai_session":"ai","service_identity":"authentication","worker_job":"worker"}
REPOSITORY_COLLECTION_METHODS = {"insert_audit_log":"audit_logs", "insert_admin_operation":"admin_operations", "insert_ai_model":"ai_models", "insert_service_identity":"service_identities", "insert_secret_reference":"secret_references", "upsert_ai_provider":"ai_providers", "update_system_config":"system_configs", "record_long_term":"long_term_memory", "list_long_term":"long_term_memory", "create_auth_credential":"auth_credentials", "create_password_reset_token":"password_reset_tokens", "create_email_verification_token":"email_verification_tokens", "register_session":"sessions"}
PY_BUILTINS = {"str": "string", "int": "int", "float": "float", "bool": "Boolean", "datetime": "date", "date": "date", "Any": "json", "dict": "json", "list": "list", "None": "void"}


def pascal(s: str) -> str:
    # Normalize snake, kebab and camel names while preserving common acronyms.
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).replace("-", "_").split("_")
    return "".join(w[:1].upper() + w[1:] for w in words if w)


def camel(s: str) -> str:
    value = pascal(s)
    return value[:1].lower() + value[1:] if value else value


def argument_specs(node):
    args=[]
    pos=list(node.args.posonlyargs)+list(node.args.args)+list(node.args.kwonlyargs)
    defaults=[None] * (len(pos)-len(node.args.defaults)) + list(node.args.defaults)
    for arg, default in zip(pos, defaults):
        if arg.arg in {"self", "cls"}: continue
        typ=annotation(arg.annotation)["type"] if arg.annotation else "string"
        args.append(f"{camel(arg.arg)} : {typ}")
    return args


def return_type(node):
    if node.returns: return annotation(node.returns)["type"]
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and child.value is not None:
            if isinstance(child.value, ast.Constant) and child.value.value is None: continue
            return "json"
    return "void"


def singular(s: str) -> str:
    if s.endswith("ies") and len(s) > 3: return s[:-3] + "y"
    if s.endswith("sses"): return s[:-2]
    if s.endswith("s") and not s.endswith("ss"): return s[:-1]
    return s


def diagram_name(code: str) -> str:
    return pascal(singular(code))


def annotation(node):
    if node is None: return "unknown"
    try: raw = ast.unparse(node)
    except Exception: raw = "unknown"
    nullable = "None" in raw or "Optional" in raw or "| None" in raw
    base = raw.replace("Optional[", "").replace("]", "").replace(" | None", "")
    if "list[" in raw.lower() or "List[" in raw: kind = "json"
    elif "dict[" in raw or "Dict[" in raw or "Any" in raw: kind = "json"
    elif base.split(".")[-1] in {"EmailStr", "UUID", "str", "SystemRole", "KYC", "Creator"}: kind="string"
    elif base.split(".")[-1] in {"bool", "Boolean"}: kind="Boolean"
    elif base.split(".")[-1] in {"int", "float", "datetime", "date"}: kind=PY_BUILTINS[base.split(".")[-1]]
    else: kind = PY_BUILTINS.get(base, PY_BUILTINS.get(base.split(".")[-1], "json"))
    if kind == "list": kind = "json"
    return {"raw": raw, "type": kind, "nullable": nullable}


def inferred_value_type(node, key=""):
    k=key.lower().split(".")[0]
    if k in {"action", "kind", "status", "system_role", "kyc_status", "creator_status", "purpose", "provider", "type"} or k == "_id" or k.endswith(("_id", "_token", "_hash", "_email", "_ip", "_role", "_status", "_code")):
        return {"raw":"inferred from key", "type":"string", "nullable":False}
    if k.endswith(("_ids","_refs")) or k in {"settings", "preferences", "details", "values", "changes", "metadata", "payload", "request", "response", "social_links", "login_security", "capabilities", "scopes", "permissions", "blocked_users", "bookmarks", "pinned_documents", "proposal"}:
        return {"raw":"inferred from key", "type":"json", "nullable":False}
    if k.endswith(("_at", "_date", "_time", "_until")) or k in {"created_at", "updated_at", "expires_at", "timestamp"}:
        return {"raw":"inferred from key", "type":"date", "nullable":False}
    if k.startswith(("is_", "has_", "can_")) or k in {"enabled", "used", "revoked", "active", "delivered", "trusted", "verified"}:
        return {"raw":"inferred from key", "type":"Boolean", "nullable":False}
    if isinstance(node, ast.Constant):
        value=node.value
        if value is None: return {"raw":"None", "type":"varchar(255)", "nullable":True}
        if isinstance(value, bool): return {"raw":"bool", "type":"Boolean", "nullable":False}
        if isinstance(value, int): return {"raw":"int", "type":"int", "nullable":False}
        if isinstance(value, float): return {"raw":"float", "type":"float", "nullable":False}
        if isinstance(value, str): return {"raw":"str", "type":"string", "nullable":False}
    expr=ast.unparse(node).lower() if node is not None else ""
    if any(x in expr for x in ("datetime.", "date.", "timestamp")):
        typ="date"
    elif isinstance(node, (ast.Dict, ast.List, ast.Set, ast.Tuple)) or k.endswith(("_refs", "_ids")) or k in {"settings", "preferences", "details", "values", "changes", "metadata", "payload", "request", "response", "social_links", "login_security", "capabilities", "proposal"}:
        typ="json"
    elif k.startswith(("is_", "has_", "can_")) or k in {"enabled", "used", "revoked", "active", "delivered", "trusted", "verified"}:
        typ="Boolean"
    elif k.endswith(("_count", "_limit", "_size", "_bytes", "_seconds", "_minutes", "_days", "_ms", "_revision", "_sequence", "_attempts", "_version")) or k in {"revision", "affected", "attempt_count", "storage_limit"}:
        typ="int"
    else:
        typ="string"
    return {"raw":"inferred from value/key", "type":typ, "nullable":node is None or (isinstance(node, ast.Constant) and node.value is None)}


def literal(node):
    try: return ast.literal_eval(node)
    except Exception: return None


def call_collection(call):
    """Get literal collection argument for mongo/repository calls."""
    func = ast.unparse(call.func).lower()
    # Only recognize direct calls on the Mongo helper. Repository/service
    # methods often take an id as their first argument; treating that literal
    # as a collection name produced false positives in the initial scan.
    if (isinstance(call.func, ast.Attribute)
        and call.func.attr in {"get", "find", "find_one", "insert_one", "update_one", "update_many", "delete_one", "count_documents"}
        and ast.unparse(call.func.value).split(".")[-1].lower() == "mongo"):
        if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
            return call.args[0].value
    # db["collection"].method(...)
    f = call.func
    if (isinstance(f, ast.Attribute) and f.attr in {"find", "find_one", "insert_one", "update_one", "update_many", "delete_one", "count_documents", "find_one_and_update", "create_index"}
        and isinstance(f.value, ast.Subscript)):
        root = f.value.value
        is_db_collection = (
            isinstance(root, ast.Name) and root.id.lower() in {"db", "database"}
        ) or (
            isinstance(root, ast.Call) and isinstance(root.func, ast.Attribute) and root.func.attr == "get_db"
        )
        key = literal(f.value.slice)
        if is_db_collection and isinstance(key, str): return key
    # Attribute-style Motor access: database.value.projects.find_one(...),
    # db.projects.create_index(...), and similar patterns.
    if isinstance(f, ast.Attribute) and f.attr in {"find", "find_one", "insert_one", "update_one", "update_many", "delete_one", "count_documents", "find_one_and_update", "create_index", "replace_one", "aggregate"} and isinstance(f.value, ast.Attribute):
        parent = f.value.value
        if isinstance(parent, ast.Attribute) and parent.attr == "value":
            return f.value.attr
        if isinstance(parent, ast.Name) and parent.id.lower() in {"db", "database"}:
            return f.value.attr
        if isinstance(parent, ast.Subscript) and isinstance(parent.value, ast.Attribute) and parent.value.attr == "mongodb":
            return f.value.attr
    if "get_collection" in func and call.args and isinstance(call.args[0], ast.Constant):
        return call.args[0].value
    return None


def dict_keys(node):
    keys = set()
    if isinstance(node, ast.Dict):
        for k in node.keys:
            if isinstance(k, ast.Constant) and isinstance(k.value, str): keys.add(k.value)
    return keys


def line(path: Path, node) -> str:
    return f"{path.relative_to(ROOT).as_posix()}:{getattr(node, 'lineno', '?')}"


def source_files(directory: Path, suffix):
    return sorted(p for p in directory.rglob("*") if p.is_file() and p.suffix in suffix and "__pycache__" not in p.parts)


def extract_service(service: str):
    base = ROOT / "backend" / service / "src"
    result = {"service": service, "collections": {}, "stores": [], "models": [], "routes": [], "service_methods": [], "repository_methods": [], "frontend": {"pages": [], "service_functions": [], "page_calls": []}, "references": [], "indexes": []}
    if not base.exists(): return result
    parsed = []
    collection_fields = defaultdict(dict)
    created_fields = defaultdict(set)
    collection_sources = defaultdict(set)
    refs = set()
    for path in source_files(base, {".py"}):
        text = path.read_text(errors="replace")
        try: tree = ast.parse(text)
        except SyntaxError: continue
        parsed.append((path, tree, text))
        # Literal collection names in db indexing and Mongo helper calls.
        self_collection_aliases = {}
        self_database_aliases = set()
        for fn in (x for x in ast.walk(tree) if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))):
            if any(isinstance(d, ast.Name) and d.id == "property" for d in fn.decorator_list):
                for sub in ast.walk(fn):
                    if isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Subscript) and isinstance(sub.value.value, ast.Attribute) and sub.value.value.attr == "mongodb":
                        self_collection_aliases[fn.name] = sub.attr
                    if isinstance(sub, ast.Attribute) and sub.attr == "mongodb": self_database_aliases.add(fn.name)
        collection_mapping_names = set()
        for assign in ast.walk(tree):
            if isinstance(assign, (ast.Assign, ast.AnnAssign)):
                target_names = [x.id for x in ast.walk(assign.targets[0]) if isinstance(x, ast.Name)] if isinstance(assign, ast.Assign) and assign.targets else ([assign.target.id] if isinstance(assign.target, ast.Name) else [])
                value = assign.value
                if any(n.lower() == "index_sets" for n in target_names) and isinstance(value, ast.Dict):
                    collection_mapping_names.update(k.value for k in value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str))
                if any(n.lower().endswith("_collections") for n in target_names) and isinstance(value, (ast.Tuple, ast.List, ast.Set)):
                    collection_mapping_names.update(x.value for x in value.elts if isinstance(x, ast.Constant) and isinstance(x.value, str))
        for coll in collection_mapping_names:
            result["collections"].setdefault(coll, {"fields": {}, "sources": [], "indexes": []})
            result["collections"][coll]["sources"].append(line(path, tree))
        for n in ast.walk(tree):
            if isinstance(n, ast.Attribute) and (
                (isinstance(n.value, ast.Attribute) and n.value.attr == "value" and ast.unparse(n.value) in {"database.value", "self.database.value"})
                or (isinstance(n.value, ast.Subscript) and isinstance(n.value.value, ast.Attribute) and n.value.value.attr == "mongodb")
                or (isinstance(n.value, ast.Attribute) and isinstance(n.value.value, ast.Name) and n.value.value.id == "self" and n.value.attr in self_database_aliases)
            ):
                if n.attr not in {"value", "client", "admin", "command", "find", "find_one", "find_one_and_update", "insert_one", "insert_many", "update_one", "update_many", "delete_one", "delete_many", "count_documents", "aggregate", "create_index", "create_indexes", "replace_one", "list_collection_names"}:
                    result["collections"].setdefault(n.attr, {"fields": {}, "sources": [], "indexes": []})
                    result["collections"][n.attr]["sources"].append(line(path, n))
            if isinstance(n, ast.Subscript):
                val = literal(n.slice)
                base_expr = ast.unparse(n.value).lower()
                is_collection_subscript = (
                    isinstance(n.value, ast.Name) and n.value.id.lower() in {"db", "database"}
                ) or (
                    isinstance(n.value, ast.Call)
                    and isinstance(n.value.func, ast.Attribute)
                    and n.value.func.attr == "get_db"
                ) or (
                    isinstance(n.value, ast.Subscript)
                    and isinstance(n.value.value, ast.Attribute)
                    and n.value.value.attr == "mongodb"
                    and isinstance(n.value.ctx, ast.Load)
                    and "settings." in ast.unparse(n.value.slice)
                )
                if isinstance(val, str) and is_collection_subscript:
                    result["collections"].setdefault(val, {"fields": {}, "sources": [], "indexes": []})
                    result["collections"][val]["sources"].append(line(path, n))
            if isinstance(n, ast.Call):
                coll = call_collection(n)
                if not coll and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Attribute) and isinstance(n.func.value.value, ast.Name) and n.func.value.value.id == "self":
                    coll = self_collection_aliases.get(n.func.value.attr)
                if not coll and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Attribute):
                    dbref=n.func.value.value
                    if isinstance(dbref,ast.Attribute) and isinstance(dbref.value,ast.Name) and dbref.value.id=="self" and dbref.attr in self_database_aliases:
                        coll=n.func.value.attr
                if not coll and isinstance(n.func, ast.Attribute): coll=REPOSITORY_COLLECTION_METHODS.get(n.func.attr)
                if coll:
                    result["collections"].setdefault(coll, {"fields": {}, "sources": [], "indexes": []})
                    result["collections"][coll]["sources"].append(line(path, n))
                    # Find document and update dictionaries in positional and keyword arguments.
                    call_args=list(n.args) + [kw.value for kw in n.keywords]
                    if any(isinstance(a, ast.Name) for a in call_args) and isinstance(n.func, ast.Attribute) and n.func.attr in REPOSITORY_COLLECTION_METHODS:
                        owner=next((fn for fn in ast.walk(tree) if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)) and fn.lineno <= n.lineno <= getattr(fn,"end_lineno",fn.lineno)),None)
                        if owner:
                            assigned={}
                            for sub in ast.walk(owner):
                                if isinstance(sub,ast.Assign) and isinstance(sub.value,ast.Dict):
                                    for target in sub.targets:
                                        if isinstance(target,ast.Name): assigned[target.id]=sub.value
                            call_args += [assigned[a.id] for a in call_args if isinstance(a,ast.Name) and a.id in assigned]
                    for arg in call_args:
                        if isinstance(arg, ast.Dict):
                            op_values = []
                            # For updates, collect the direct keys inside each
                            # Mongo operator. Keep nested documents as one JSON
                            # field instead of flattening all nested keys.
                            if any(k and k.startswith("$") for k in dict_keys(arg)):
                                for key, value in zip(arg.keys, arg.values):
                                    if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value.startswith("$") and isinstance(value, ast.Dict):
                                        op_values.extend((value, k.value, v) for k,v in zip(value.keys,value.values) if isinstance(k, ast.Constant) and isinstance(k.value,str))
                            else:
                                op_values.extend((arg, k.value, v) for k,v in zip(arg.keys,arg.values) if isinstance(k, ast.Constant) and isinstance(k.value,str))
                            for dict_node, raw_key, field_value in op_values:
                                if raw_key not in {"$set", "$setOnInsert", "$push", "$inc", "$unset", "$addToSet", "$pull", "$or", "$and", "$in", "$ne", "$gt", "$gte", "$lt", "$lte", "$exists", "$type", "$regex", "$options", "$cond", "$ifNull", "$add", "$$REMOVE"}:
                                    k=raw_key.split(".")[0]
                                    item=collection_fields[coll].setdefault(k, {"type": None, "nullable": True, "evidence": []})
                                    candidate=inferred_value_type(field_value, raw_key)
                                    semantic_override=(k=="_id" or k.endswith(("_id","_ids","_hash","_token","_at","_until")) or k in {"login_security","request","payload","settings","details","values","changes","metadata","capabilities","scopes","permissions","blocked_users","bookmarks","pinned_documents"})
                                    if semantic_override or item["type"] is None or item["type"].get("type")=="varchar(255)" or (item["type"].get("raw")=="inferred from value/key" and candidate["type"]!="string"):
                                        item["type"]=candidate
                                    is_create_call=(isinstance(n.func,ast.Attribute) and (n.func.attr in {"insert_one","insert_many","record_long_term"} or n.func.attr.startswith(("insert_","create_")) or any(kw.arg=="upsert" and isinstance(kw.value,ast.Constant) and kw.value.value is True for kw in n.keywords)))
                                    if is_create_call and "." not in raw_key and not raw_key.startswith("$"):
                                        created_fields[coll].add(k)
                                    item["evidence"].append(line(path, dict_node))
                # Detect index creation.
                if isinstance(n.func, ast.Attribute) and "create_index" in n.func.attr:
                    result["indexes"].append({"at": line(path, n), "expression": ast.unparse(n)})
        # Pydantic/dataclass fields.
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                fields = []
                for stmt in node.body:
                    if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                        alias_id=stmt.target.id == "id" and isinstance(stmt.value, ast.Call) and "alias='_id'" in ast.unparse(stmt.value).replace('"', "'")
                        if not alias_id:
                            fields.append({"code": stmt.target.id, "diagram": pascal(stmt.target.id), "type": annotation(stmt.annotation), "line": line(path, stmt)})
                if fields:
                    result["models"].append({"name": node.name, "bases":[b.id for b in node.bases if isinstance(b,ast.Name)], "file": path.relative_to(ROOT).as_posix(), "fields": fields})
            # Service and repository methods; public only excludes underscore methods.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                parent = next((p for p, t, _ in parsed if t is tree), path)
                rel = parent.relative_to(base).as_posix()
                args = argument_specs(node)
                ret = return_type(node)
                calls=[child.func.attr for child in ast.walk(node) if isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute)]
                call_targets=[f"{child.func.value.id}.{child.func.attr}" for child in ast.walk(node) if isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute) and isinstance(child.func.value,ast.Name)]
                owner=next((cls.name for cls in ast.walk(tree) if isinstance(cls,ast.ClassDef) and any(part is node for part in ast.walk(cls))),None)
                used_collections=[]
                for child in ast.walk(node):
                    if isinstance(child,ast.Call):
                        used=call_collection(child)
                        if not used and isinstance(child.func,ast.Attribute) and isinstance(child.func.value,ast.Attribute) and isinstance(child.func.value.value,ast.Name) and child.func.value.value.id=="self":
                            used=self_collection_aliases.get(child.func.value.attr)
                        if used: used_collections.append(used)
                rec = {"name": node.name, "args": args, "return": ret, "line": line(path, node), "file": rel, "owner":owner, "calls":sorted(set(calls)), "call_targets":sorted(set(call_targets)), "collections":sorted(set(used_collections))}
                if "/services/" in "/" + rel: result["service_methods"].append(rec)
                if "/repositories/" in "/" + rel: result["repository_methods"].append(rec)
            # FastAPI handlers using router decorators.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr.lower() in {"get", "post", "put", "patch", "delete"}:
                        route = literal(dec.args[0]) if dec.args else ""
                        if route is not None:
                            calls=[child.func.attr for child in ast.walk(node) if isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute)]
                            call_targets=[f"{child.func.value.id}.{child.func.attr}" for child in ast.walk(node) if isinstance(child,ast.Call) and isinstance(child.func,ast.Attribute) and isinstance(child.func.value,ast.Name)]
                            result["routes"].append({"method": dec.func.attr.upper(), "path": route, "name": node.name, "args": argument_specs(node), "return": return_type(node), "line": line(path, node), "calls":sorted(set(calls)), "call_targets":sorted(set(call_targets))})
        # Pattern fallback for router.add_api_route calls, including loops.
        for m in re.finditer(r"add_api_route\s*\(\s*([^,]+),\s*([^,]+),([\s\S]*?)\)", text):
            meths = re.findall(r"['\"](GET|POST|PUT|PATCH|DELETE)['\"]", m.group(3), re.I)
            route = m.group(1).strip().strip("\"'")
            handler = m.group(2).strip().split(".")[-1]
            for meth in meths or ["GET"]:
                result["routes"].append({"method": meth.upper(), "path": route, "name": handler, "args": [], "return": "unknown", "line": f"{path.relative_to(ROOT).as_posix()}:{text.count(chr(10),0,m.start())+1}", "dynamic": True})
        # Field names serving as logical references.
        for m in re.finditer(r"['\"]([A-Za-z][A-Za-z0-9_]*(?:_id|_ids))['\"]", text):
            refs.add((m.group(1), f"{path.relative_to(ROOT).as_posix()}:{text.count(chr(10),0,m.start())+1}"))
    # Merge fields from operations and model schemas; map fields to collections when unique.
    collection_names = set(result["collections"])
    for coll in collection_names:
        for key, item in collection_fields[coll].items():
            result["collections"][coll]["fields"].setdefault(key, {"type": item["type"] or {"raw":"inferred from value", "type":"varchar(255)", "nullable":True}, "evidence": sorted(set(item["evidence"]))})
    # Attach model fields to collections by matching singular/plural class names and obvious auth User.
    models_by_name={m["name"]:m for m in result["models"]}
    def inherited_fields(model, seen=None):
        seen=seen or set()
        if model["name"] in seen: return list(model["fields"])
        seen.add(model["name"])
        vals=[]
        for b in model.get("bases",[]):
            if b in models_by_name: vals.extend(inherited_fields(models_by_name[b],seen))
        vals.extend(model["fields"])
        unique={x["code"]:x for x in vals}
        return list(unique.values())
    for model in result["models"]:
        if re.search(r"(Create|Update|Response|Request|Input|Payload)$",model["name"]): continue
        model_base = re.sub(r"(Base|InDB|Read|Model|Schema|Record)$", "", model["name"])
        candidates = [c for c in collection_names if singular(c).lower() == model_base.lower() or diagram_name(c).lower() == model_base.lower()]
        if service == "authentication" and model["name"].startswith("User"): candidates = ["auth_credentials"] if "auth_credentials" in collection_names else []
        if len(candidates) == 1:
            coll = candidates[0]
            for f in inherited_fields(model):
                result["collections"][coll]["fields"][f["code"]]={"type": f["type"], "evidence": [f["line"]]}
                if service=="authentication" and model["name"]=="UserBase" and f["code"] not in {"password","agreed_to_terms"}:
                    created_fields[coll].add(f["code"])
    schema_collection_map={
        "authentication":{"ProviderUpdate":"ai_providers", "ModelRegistryEntry":"ai_models", "ServiceIdentityRequest":"service_identities", "SecretReferenceRequest":"secret_references"}
    }.get(service,{})
    for model in result["models"]:
        coll=schema_collection_map.get(model["name"])
        if coll in result["collections"]:
            for f in inherited_fields(model):
                if f["code"] in {"reason", "confirmation"}: continue
                result["collections"][coll]["fields"][f["code"]]={"type":f["type"],"evidence":[f["line"]]}
    if service=="ai":
        qmodel=models_by_name.get("QdrantPointPayload")
        if qmodel:
            vector_source=ROOT/"backend/ai/src/store/vector.py"
            vector_text=vector_source.read_text(errors="replace")
            match=re.search(r"self\.collection_name\s*=\s*['\"]([^'\"]+)['\"]",vector_text)
            result["stores"].append({"kind":"Qdrant vector collection","name":match.group(1) if match else "unknown", "fields":inherited_fields(qmodel), "source":vector_source.relative_to(ROOT).as_posix()})
    for coll, data in result["collections"].items():
        for field,fd in data["fields"].items():
            if fd.get("type",{}).get("nullable"):
                continue
            if field not in created_fields[coll]:
                fd["type"]["nullable"]=True
        data["fields"] = dict(sorted(data["fields"].items()))
        data["sources"] = sorted(set(data["sources"]))
    # Bind identifier-like fields to the collection document that actually
    # contains them before resolving the target collection.
    for field, at in sorted(refs):
        target = ""
        base_target = field[:-4] if field.endswith("_ids") else field[:-3]
        if service=="authentication" and base_target in {"user","account"}: base_target="auth_credential"
        for coll in collection_names:
            if singular(coll).lower() == base_target.lower() or coll.lower() == base_target.lower() + "s": target = coll; break
        if target:
            for source,data in result["collections"].items():
                if field in data["fields"]:
                    result["references"].append({"source":source,"field": field, "target": target, "at": at, "inferred": True})
    result["references"]=list({(r["source"],r["field"],r["target"]):r for r in result["references"]}.values())
    result["external_references"]=[]
    for field,at in sorted(refs):
        if not field.endswith(("_id","_ids")): continue
        stem=field[:-4] if field.endswith("_ids") else field[:-3]
        if service=="authentication" and stem in {"user","account"}: stem="auth_credential"
        target_service=EXTERNAL_REFERENCE_SERVICES.get(stem)
        if target_service and target_service!=service:
            for source,data in result["collections"].items():
                if field in data["fields"]:
                    result["external_references"].append({"source":source,"field":field,"target_service":target_service,"target_concept":"AuthCredential" if service=="authentication" and stem=="auth_credential" else pascal(stem),"at":at,"inferred":True})
    result["external_references"]=list({(r["source"],r["field"],r["target_service"]):r for r in result["external_references"]}.values())
    repo_by_name={m["name"]:m.get("collections",[]) for m in result["repository_methods"]}
    for method in result["service_methods"]:
        method["collections"]=sorted({collection for called in method.get("calls",[]) for collection in repo_by_name.get(called,[])})
    extract_frontend(service, result)
    return result


def extract_frontend(service, result):
    feat = ROOT / "frontend" / "features" / service
    app = ROOT / "frontend" / "app"
    if feat.exists():
        for p in source_files(feat, {".js", ".jsx", ".mjs", ".ts", ".tsx"}):
            txt = p.read_text(errors="replace")
            if re.search(r"export\s+(?:async\s+)?function\s+\w+|export\s+const\s+\w+\s*=\s*(?:async\s*)?\(", txt):
                names = re.findall(r"export\s+(?:async\s+)?function\s+(\w+)|export\s+const\s+(\w+)\s*=", txt)
                for pair in names:
                    name = next((x for x in pair if x), None)
                    if name: result["frontend"]["service_functions"].append({"name":name,"file":p.relative_to(ROOT).as_posix()})
    # route page wrappers and pages explicitly imported from this feature
    for p in source_files(app, {".js", ".jsx", ".ts", ".tsx"}):
        if p.name not in {"page.js", "page.jsx", "page.ts", "page.tsx"}: continue
        txt = p.read_text(errors="replace")
        match = re.search(r"from\s+['\"]@/features/"+re.escape(service)+r"/([^'\"]+)['\"]", txt)
        if match:
            page = match.group(1).split("/")[-1]
            result["frontend"]["pages"].append({"name":page,"route_file":p.relative_to(ROOT).as_posix(),"feature_file":f"frontend/features/{service}/{match.group(1)}"})
    result["frontend"]["pages"].sort(key=lambda x:x["route_file"])
    result["frontend"]["service_functions"].sort(key=lambda x:(x["file"],x["name"]))


def json_type(ft):
    typ = ft.get("type", {}).get("type", "varchar(255)") if isinstance(ft.get("type"), dict) else "varchar(255)"
    return {"string":"varchar(255)", "int":"integer(10)", "float":"float(10)", "Boolean":"boolean", "date":"datetime", "json":"json", "varchar(255)":"varchar(255)"}.get(typ, "varchar(255)")


def attr_name(code): return pascal(code)


def field_name(collection, field):
    if field == "_id": return diagram_name(collection) + "Id"
    if field.endswith("_id"): return pascal(field[:-3]) + "Id"
    return attr_name(field)


def write_service(spec):
    service=spec["service"]; dest=OUT/service; dest.mkdir(parents=True,exist_ok=True)
    (dest/"spec.json").write_text(json.dumps(spec,indent=2,ensure_ascii=False)+"\n")
    # Rename map: collection, fields, methods, pages, routes, with direct evidence.
    rows=["# Rename map — "+service,"","Tên code | Tên sơ đồ | Loại | Căn cứ","---|---|---|---"]
    for c,d in spec["collections"].items():
        rows.append(f"`{c}` | `{diagram_name(c)}` | collection/table | `{', '.join(d['sources'][:3])}`")
        for f,fd in d["fields"].items():
            ev=", ".join(fd.get("evidence",[])[:2])
            rows.append(f"`{f}` | `{field_name(c, f)}` | field | `{ev or 'collection document/query; see spec.json'}`")
    for m in spec["service_methods"]+spec["repository_methods"]:
        rows.append(f"`{m['name']}` | `{pascal(m['name'])}` | method | `{m['line']}`")
    for p in spec["frontend"]["pages"]: rows.append(f"`{p['name']}` | `GD_{pascal(p['name'])}` | page/boundary | `{p['route_file']}`")
    for r in spec["routes"]: rows.append(f"`{r['name']}` | `Ctrl_{pascal(Path(r['line'].split(':')[0]).stem)}` | route method in grouped control | `{r['line']}`")
    (dest/"rename_map.md").write_text("\n".join(rows)+"\n")
    # Domain candidates exclude technical collections per V6.
    domain=[]; excluded=[]
    for c,d in spec["collections"].items():
        if TECH.search(c): excluded.append(c); continue
        domain.append((c,d))
    spec_lines=[f"# {service} — generated specification", "", "> Generated by `vp_diagram_out/tools/extract.py`; source evidence is included per item. Static extraction may miss dynamically assembled MongoDB documents or relationships.", "", "## Inventory", f"- Collections: {len(spec['collections'])}", f"- Pydantic/dataclass-like model classes with annotated fields: {len(spec['models'])}", f"- Router handlers found: {len(spec['routes'])}", f"- Public service methods: {len(spec['service_methods'])}", f"- Public repository methods: {len(spec['repository_methods'])}", f"- Frontend pages mapped by app-route import: {len(spec['frontend']['pages'])}", "", "## Domain model candidates"]
    dclasses=[]; dattrs=0
    for c,d in domain:
        fields=list(d["fields"]); dattrs += 1 + sum(1 for f in fields if f != "_id" and not f.endswith(("_id", "_ids"))); dclasses.append(diagram_name(c))
        spec_lines.append(f"- `{diagram_name(c)}`: "+", ".join(f"`{field_name(c, f)}`" for f in fields)+f" — source: {', '.join(d['sources'][:3]) or 'field evidence in spec.json'}")
    spec_lines += ["", "## ERD collections and fields"]
    total_fields=0
    for c,d in spec["collections"].items():
        spec_lines.append(f"### {diagram_name(c)} (code collection `{c}`; technical={bool(TECH.search(c))})")
        for f,fd in d["fields"].items():
            total_fields+=1; typ=json_type(fd); nullable="N" if fd.get("type",{}).get("nullable",True) else "NOT NULL"
            if f=="_id": nullable="PK"
            spec_lines.append(f"- `{field_name(c, f)}` `{typ}` [{nullable}] — {', '.join(fd.get('evidence',[])[:2]) or 'schema/collection evidence in spec.json'}")
    if spec["stores"]:
        spec_lines += ["", "## Non-MongoDB vector store"]
        for store in spec["stores"]:
            spec_lines.append(f"### {store['kind']} `{store['name']}` — source `{store['source']}`")
            for field in store["fields"]:
                spec_lines.append(f"- `{field['diagram']}` `{json_type({'type':field['type']})}` — `{field['line']}`")
    spec_lines += ["", "## Local logical references"]
    for ref in spec["references"]: spec_lines.append(f"- `{diagram_name(ref['source'])}.{field_name(ref['source'],ref['field'])}` → `{diagram_name(ref['target'])}.{diagram_name(ref['target'])}Id` [SUY RA], source `{ref['at']}`")
    if not spec["references"]: spec_lines.append("- No local reference candidate was inferred by the scanner.")
    spec_lines += ["", "## BCE function inventory", "### Routes"]
    for r in spec["routes"]: spec_lines.append(f"- `{r['method']} {r['path']}` `{r['name']}({', '.join(r['args'])}) : {r['return']}` — `{r['line']}`"+(" [dynamic route template]" if r.get("dynamic") else ""))
    spec_lines += ["", "### Service methods"]
    for m in spec["service_methods"]: spec_lines.append(f"- `{m['name']}({', '.join(m['args'])}) : {m['return']}` — `{m['line']}`")
    spec_lines += ["", "### Repository methods"]
    for m in spec["repository_methods"]: spec_lines.append(f"- `{m['name']}({', '.join(m['args'])}) : {m['return']}` — `{m['line']}`")
    spec_lines += ["", "### Frontend pages"]
    for p in spec["frontend"]["pages"]: spec_lines.append(f"- `{p['name']}` from `{p['route_file']}` → `{p['feature_file']}`")
    (dest/"spec.md").write_text("\n".join(spec_lines)+"\n")
    # Domain prompt, with complete extracted attributes and ref-derived links among candidate domain classes.
    domain_prompt=["Domain Model (UML class diagram: attributes only, no operations, no reference fields)", f"Create the {service} domain model. Use PascalCase English names. Each class has a primary key named '<ClassName>Id'."]
    for c,d in domain:
        fields=[f"'{diagram_name(c)}Id' (PK)"]+[f"'{field_name(c, f)}'" for f in d["fields"] if f != "_id" and not f.endswith("_id") and not f.endswith("_ids")]
        domain_prompt.append(f"Class '{diagram_name(c)}': attributes "+", ".join(fields)+".")
    rels=[]
    domain_names={c for c,_ in domain}
    for ref in spec["references"]:
        if ref["source"] in domain_names and ref["target"] in domain_names:
            rels.append((ref["source"],ref["target"],ref["field"]))
    if rels:
        for i,(a,b,f) in enumerate(rels,1): domain_prompt.append(f"({i}) '{diagram_name(a)}' association '{diagram_name(b)}', multiplicity at '{diagram_name(a)}': 0..*, multiplicity at '{diagram_name(b)}': 1, navigable from '{diagram_name(a)}' to '{diagram_name(b)}'.")
    else: domain_prompt.append("Every listed class has no relationships.")
    domain_prompt.append(f"Include EVERY class, attribute, operation and relationship listed above, exactly as named. Do not omit, merge, rename, simplify, summarize or add anything. Do not invent extra classes, attributes or relationships. If something does not fit, keep it and let the layout grow instead of dropping it. Totals: {len(domain)} classes, {len(rels)} relationships, {dattrs} attributes.")
    domain_prompt += ["", f"Checklist: classes={len(domain)}; relationships={len(rels)}; attributes={dattrs}.", "Correction prompt: Fix only the following items and keep everything else unchanged: [insert verified discrepancy]."]
    (dest/"P1_domain.txt").write_text("\n".join(domain_prompt)+"\n")
    # ERD prompt emits every field, counts are script totals.
    erd=["Logical Entity Relationship Diagram of MongoDB collections: fields with types, _id as primary key, logical references shown with crow's foot", f"Create the logical MongoDB ERD for service '{service}'. Use the following PascalCase names for every collection and field. These are logical references, not enforced foreign keys."]
    for c,d in spec["collections"].items():
        fields=[]
        for f,fd in d["fields"].items():
            fields.append(f"'{field_name(c, f)}' {json_type(fd)}"+(" [PK]" if f=="_id" else (" [N]" if fd.get("type",{}).get("nullable",True) else "")))
        erd.append(f"Table '{diagram_name(c)}' ({'technical' if TECH.search(c) else 'business/data'}): "+"; ".join(fields)+".")
    vector_count=0
    for store in spec["stores"]:
        vector_count+=len(store["fields"])
        fields="; ".join(f"'{pascal(f['code'])}' {json_type({'type':f['type']})}" for f in store["fields"])
        erd.append(f"Separate vector store '{pascal(store['name'])}' of kind '{store['kind']}', not a MongoDB table; payload fields: {fields}.")
    for i,ref in enumerate(spec["references"],1):
        source_name=diagram_name(ref['source']); target_name=diagram_name(ref['target']); source_mult="0..*" if not ref["field"].endswith("_ids") else "0..*"
        erd.append(f"({i}) '{source_name}' association '{target_name}', multiplicity at '{source_name}': {source_mult}, multiplicity at '{target_name}': 1, navigable from '{source_name}' to '{target_name}'; field '{field_name(ref['source'],ref['field'])}', label 'logical reference (not enforced)'.")
    erd.append(f"Include EVERY table, field and relationship listed above, exactly as named. Do not omit, merge, rename, simplify, summarize or add anything. Do not invent extra tables, fields or relationships. If something does not fit, keep it and let the layout grow instead of dropping it. Totals: {len(spec['collections'])} MongoDB tables, {len(spec['references'])} logical relationships, {total_fields} MongoDB fields; {len(spec['stores'])} separate vector stores and {vector_count} vector payload fields.")
    erd += ["", f"Checklist: tables={len(spec['collections'])}; relationships={len(spec['references'])}; fields={total_fields}.", "Correction prompt: Fix only the following items and keep everything else unchanged: [insert verified discrepancy]."]
    (dest/"P2_erd.txt").write_text("\n".join(erd)+"\n")
    # BCE prompts grouped by router file: one control per router as required by V6.
    entities=[(c, diagram_name(c)) for c,_ in spec["collections"].items()]
    route_groups=defaultdict(list)
    for r in spec["routes"]: route_groups[Path(r["line"].split(":")[0]).stem].append(r)
    group_list=[]
    for name,rs in route_groups.items(): group_list.append(("router_"+name,rs,[]))
    method_groups=defaultdict(list)
    for method in spec["service_methods"]: method_groups[method.get("owner") or Path(method["file"]).stem].append(method)
    for name,ms in method_groups.items(): group_list.append(("service_"+name,[],ms))
    if spec["frontend"]["pages"]: group_list.append(("frontend_pages",[],[]))
    if not group_list: group_list=[("service_core",[],[])]
    bce_status=[]
    for group,rs,ms in group_list:
        bce=["UML Class Diagram (Boundary-Control-Entity analysis)", f"Create the BCE class diagram for '{service}', group '{group}'. Use English PascalCase names. Use stereotypes <<boundary>>, <<control>>, <<entity>>. Do not connect boundaries directly to entities."]
        classes=0; rel_count=0; total_attr=0
        stem=group.removeprefix("router_")
        if group.startswith("service_"): stem=group[len("service_"):]
        stem=stem.removeprefix("service_")
        control_name="Ctrl_"+pascal(stem)
        if rs:
            operations=[]
            for r in rs:
                args=", ".join(r["args"])
                operations.append(f"+ {pascal(r['name'])}({args}) : {r['return']}")
            bce.append(f"Class '{control_name}' <<control>>: "+"; ".join(operations)+".")
            classes+=1
        elif ms:
            operations=[f"+ {pascal(m['name'])}({', '.join(m['args'])}) : {m['return']}" for m in ms]
            bce.append(f"Class '{control_name}' <<control>>: "+"; ".join(operations)+".")
            classes+=1
        elif group=="frontend_pages":
            for page in spec["frontend"]["pages"]:
                bce.append(f"Class 'GD_{pascal(page['name'])}' <<boundary>>: source '{page['route_file']}'.")
                classes+=1
        used_methods=list(ms)
        if rs:
            route_targets={name for r in rs for name in r.get("call_targets",[])}
            called_service_methods=[m for m in spec["service_methods"] if m.get("owner") and f"{m['owner']}.{m['name']}" in route_targets]
            by_service=defaultdict(list)
            for method in called_service_methods: by_service[method["owner"]].append(method)
            used_methods += called_service_methods
            for service_class, service_ops in by_service.items():
                service_control="Ctrl_"+pascal(service_class)
                operations="; ".join(f"+ {pascal(m['name'])}({', '.join(m['args'])}) : {m['return']}" for m in service_ops)
                bce.append(f"Class '{service_control}' <<control>>: {operations}.")
                classes+=1
                bce.append(f"Control dependency: '{control_name}' to '{service_control}', multiplicity at source: 1, multiplicity at target: 1, navigable from source to target.")
                rel_count+=1
        # Include local collection entities touched by repository methods from
        # the same service. Repository method inventories remain in spec.md.
        used=set(c for m in used_methods for c in m.get("collections",[]))
        collection_owners=defaultdict(set)
        for method in used_methods:
            owner_name=method.get("owner")
            for coll in method.get("collections",[]):
                if owner_name: collection_owners[coll].add(owner_name)
        repo_by_coll=defaultdict(list)
        for m in spec["repository_methods"]:
            for coll in m.get("collections",[]): repo_by_coll[coll].append(m)
        for code_name, ent in entities:
            if code_name in used:
                repo_methods=repo_by_coll[code_name]
                ops="; ".join(f"+ {pascal(m['name'])}({', '.join(m['args'])}) : {m['return']}" for m in repo_methods)
                bce.append(f"Class '{ent}' <<entity>>: - {ent}Id : string"+(f"; {ops}" if ops else "")+".")
                classes+=1; total_attr+=1
                source_owners=collection_owners.get(code_name, set())
                if ms and source_owners:
                    source_owners={ms[0].get("owner")}
                for source_owner in sorted(x for x in source_owners if x):
                    source_control=control_name if ms else ("Ctrl_"+pascal(source_owner))
                    bce.append(f"Control dependency: '{source_control}' to '{ent}', multiplicity at control: 1, multiplicity at entity: 1, navigable from control to entity.")
                    rel_count+=1
        bce.append(f"Include EVERY class, attribute, operation and relationship listed above, exactly as named. Do not omit, merge, rename, simplify, summarize or add anything. Do not invent extra classes, attributes or relationships. If something does not fit, keep it and let the layout grow instead of dropping it. Totals: {classes} classes, {rel_count} relationships, {total_attr} attributes.")
        bce += ["", f"Checklist: classes={classes}; relationships={rel_count}; attributes={total_attr}.", "Correction prompt: Fix only the following items and keep everything else unchanged: [insert verified discrepancy]."]
        filename=f"P3_bce_{re.sub(r'[^a-z0-9_]+','_',group.lower())}.txt"
        (dest/filename).write_text("\n".join(bce)+"\n"); bce_status.append(filename)
    # Review assumptions and exclusions.
    review=[f"# Review — {service}", "", "## [SUY RA]", "- Field-only references and multiplicities are inferred from identifier naming and static query/write evidence; MongoDB does not enforce these relationships.", "- Missing type hints on extracted document keys default to `varchar(255)` as required by V6.", "- Optionality defaults to nullable when a write path or annotation does not guarantee presence.", "", "## Excluded from Domain Model", "| Collection | Reason |", "|---|---|"]
    for c in excluded: review.append(f"| `{c}` | Technical/infrastructure collection excluded by V6 rule |")
    review += ["", "## Code ambiguities / possible issues", "- Dict-shaped and update-only fields are merged from static key evidence. The scanner cannot prove every runtime payload shape.", "- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.", "- The scanner does not modify source application code.", "", "## Extraction coverage", f"- Routes extracted: {len(spec['routes'])}; dynamic route entries: {sum(bool(x.get('dynamic')) for x in spec['routes'])}.", f"- Collections extracted: {len(spec['collections'])}; collections with no detected fields: {sum(not x['fields'] for x in spec['collections'].values())}.", f"- Separate vector stores extracted: {len(spec['stores'])}.", "- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code."]
    (dest/"review.md").write_text("\n".join(review)+"\n")
    return {"service":service,"collections":len(spec["collections"]),"routes":len(spec["routes"]),"pages":len(spec["frontend"]["pages"]),"domain_classes":len(domain),"domain_attributes":dattrs,"erd_fields":total_fields,"bce_groups":len(bce_status),"bce_files":bce_status}


def main():
    OUT.mkdir(exist_ok=True)
    overrides=OUT/"overrides.json"
    if not overrides.exists(): overrides.write_text(json.dumps({"note":"Add static-extraction corrections here; script currently records but does not silently guess route expansions."},indent=2)+"\n")
    summaries=[]
    for service in SERVICES:
        spec=extract_service(service)
        summaries.append(write_service(spec))
    # inter-service dependencies and overview prompt/spec
    overview=OUT/"00_overview"; overview.mkdir(exist_ok=True)
    deps=[]
    for service in SERVICES:
        base=ROOT/"backend"/service/"src"
        for p in source_files(base,{".py"}):
            txt=p.read_text(errors="replace")
            for target in SERVICES:
                if target != service and re.search(rf"['\"]{re.escape(target)}['\"]",txt): deps.append((service,target,p.relative_to(ROOT).as_posix()))
    dep_rows=sorted(set(deps))
    overview_lines=["# Veriq system overview", "", "## Service extraction totals", "Service | Collections | Route handlers | Frontend pages | Domain classes | ERD fields | BCE groups", "---|---:|---:|---:|---:|---:|---:"]
    for s in summaries: overview_lines.append(f"{s['service']} | {s['collections']} | {s['routes']} | {s['pages']} | {s['domain_classes']} | {s['erd_fields']} | {s['bce_groups']}")
    overview_lines += ["", "## Static inter-service references", "Caller | Referenced service | Evidence", "---|---|---"]
    for a,b,e in dep_rows: overview_lines.append(f"{a} | {b} | `{e}`")
    (overview/"spec.md").write_text("\n".join(overview_lines)+"\n")
    # Self-contained system domain prompt, assembled from extracted service specs.
    all_domain=[]; domain_by_service={}; all_attrs=0
    for service in SERVICES:
        spec=json.loads((OUT/service/"spec.json").read_text())
        excluded=set(spec.get("excluded",[]))
        entities=[(c,d) for c,d in spec["collections"].items() if not TECH.search(c) and c not in excluded]
        domain_by_service[service]={diagram_name(c) for c,_ in entities}
        for c,d in entities:
            fields=[field_name(c,f) for f in d["fields"] if f!="_id" and not f.endswith(("_id","_ids"))]
            all_domain.append((service,c,diagram_name(c),fields))
            all_attrs+=1+len(fields)
    overview_prompt=["Domain Model (UML class diagram: attributes only, no operations, no reference fields)","Create the Veriq system-level business domain model. Use the exact PascalCase class and attribute names below. Each class has a primary key named '<ClassName>Id'. Include only listed classes and attributes."]
    for service,c,name,fields in all_domain:
        overview_prompt.append(f"Class '{name}' (service '{service}'): attributes "+", ".join([f"'{name}Id' (PK)"]+[f"'{f}'" for f in fields])+".")
    class_service={name:service for service,_,name,_ in all_domain}
    cross=[]; seen=set()
    for service in SERVICES:
        spec=json.loads((OUT/service/"spec.json").read_text())
        for ref in spec.get("external_references",[]):
            source=diagram_name(ref["source"]); target=ref["target_concept"]; target_service=ref["target_service"]
            if target_service=="authentication" and target.lower() in {"user","actor","requester","reviewer","owneruser","targetuser","createdby","updatedby","deletedby"}:
                target="AuthCredential"
            if source not in domain_by_service.get(service,set()) or target not in domain_by_service.get(target_service,set()):
                continue
            key=(service,source,target_service,target,ref["field"])
            if key not in seen: seen.add(key); cross.append((service,source,ref["field"],target_service,target))
    for i,(ss,source,field,ts,target) in enumerate(cross,1):
        overview_prompt.append(f"({i}) '{source}' association '{target}', source service '{ss}', target service '{ts}', multiplicity at '{source}': 0..*, multiplicity at '{target}': 1, navigable from '{source}' to '{target}'; code field `{field}` [SUY RA].")
    if not cross: overview_prompt.append("Every listed class has no cross-service relationships supported by extracted identifier fields.")
    overview_prompt.append(f"Include EVERY class, attribute and listed relationship, exactly as named. Do not omit, merge, rename, simplify, summarize or add anything. Do not invent extra classes, attributes or relationships. If something does not fit, keep it and let the layout grow instead of dropping it. Totals: {len(all_domain)} classes, {len(cross)} cross-service relationships, {all_attrs} attributes.")
    overview_prompt += ["",f"Checklist: classes={len(all_domain)}; relationships={len(cross)}; attributes={all_attrs}.","Correction prompt: Fix only the following items and keep everything else unchanged: [insert verified discrepancy]."]
    (overview/"P1_domain.txt").write_text("\n".join(overview_prompt)+"\n")
    progress=["# VP diagram extraction progress", "", "Generated by `vp_diagram_out/tools/extract.py`.", "", "Service | Domain | ERD | BCE | Status", "---|---|---|---|---"]
    for s in summaries: progress.append(f"{s['service']} | {s['domain_classes']} classes / {s['domain_attributes']} attributes | {s['collections']} tables / {s['erd_fields']} fields | {s['bce_groups']} groups | generated")
    progress += ["", "## Remaining", "- Review extraction evidence and adjust `overrides.json` for any missed dynamic collections, routes or frontend-to-API call mappings.", "- Refine generated BCE controls and association targets against each concrete route/service/repository call chain.", "- Complete system-level overview relationships and prompts from confirmed cross-service references.", "- No application code was modified; this work writes only under `vp_diagram_out/`."]
    (OUT/"PROGRESS.md").write_text("\n".join(progress)+"\n")
    print(json.dumps(summaries,indent=2,ensure_ascii=False))

if __name__ == "__main__": main()
