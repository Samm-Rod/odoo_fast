import os
import xmlrpc.client
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = os.getenv("ODOO_URL")
ODOO_DB = os.getenv("ODOO_DB")
ODOO_USER = os.getenv("ODOO_USER")
ODOO_API_KEY = os.getenv("ODOO_API_KEY")

app = FastAPI(title="Odoo Integration API")

_uid_cache = None


def get_uid():
    global _uid_cache
    if _uid_cache is None:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        _uid_cache = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
        if not _uid_cache:
            raise HTTPException(status_code=401, detail="Falha na autenticação com Odoo")
    return _uid_cache


def get_models_proxy():
    return xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")


class PartnerCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None


class PartnerUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None


@app.get("/")
def root():
    return {"status": "ok", "message": "Odoo Integration API rodando"}


@app.get("/partners")
def list_partners(limit: int = 20):
    uid = get_uid()
    models = get_models_proxy()
    try:
        partners = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search_read',
            [[]],
            {'fields': ['id', 'name', 'email', 'phone'], 'limit': limit}
        )
        return partners
    except xmlrpc.client.Fault as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/partners/{partner_id}")
def get_partner(partner_id: int):
    uid = get_uid()
    models = get_models_proxy()
    try:
        result = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'read',
            [[partner_id]], {'fields': ['id', 'name', 'email', 'phone']}
        )
    except xmlrpc.client.Fault as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail="Parceiro não encontrado")
    return result[0]


@app.post("/partners")
def create_partner(partner: PartnerCreate):
    uid = get_uid()
    models = get_models_proxy()
    try:
        new_id = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'create',
            [partner.model_dump(exclude_none=True)]
        )
        return {"id": new_id}
    except xmlrpc.client.Fault as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/partners/{partner_id}")
def update_partner(partner_id: int, partner: PartnerUpdate):
    uid = get_uid()
    models = get_models_proxy()
    data = partner.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
    try:
        models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'write',
            [[partner_id], data]
        )
    except xmlrpc.client.Fault as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "updated"}


@app.delete("/partners/{partner_id}")
def delete_partner(partner_id: int):
    uid = get_uid()
    models = get_models_proxy()
    try:
        models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'unlink',
            [[partner_id]]
        )
    except xmlrpc.client.Fault as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "deleted"}


# Roda: uvicorn main:app --reload 