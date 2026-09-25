"""Serialização de BronzeRecord/SilverRecord/EvalResult para trafegar via XCom
do Airflow.

Sem dependência de `airflow` -- testável no host normalmente. Necessário porque:
1. XCom (backend padrão, no metadata DB) só serializa JSON nativamente --
   dataclasses não são JSON-serializáveis por padrão.
2. `BronzeRecord.raw_content` pode ser `bytes` (ex.: PDF do PRODIST), que nem
   JSON aceita -- por isso o base64 explícito abaixo.

Limitação conhecida: XCom no backend padrão tem limite de tamanho (a
depender do metadata DB); um PDF grande em base64 pode estourar esse limite.
Quando isso importar de verdade, a solução é um XCom backend customizado
apontando para o `bronze_destination` (Cloud Storage) em vez de passar o
conteúdo inteiro pelo XCom -- fora do escopo deste passo do roadmap.
"""

import base64
from dataclasses import asdict

from core.contracts import BronzeRecord, EvalResult, SilverRecord


def serialize_bronze(record: BronzeRecord) -> dict:
    data = asdict(record)
    if isinstance(data["raw_content"], bytes):
        data["raw_content"] = base64.b64encode(data["raw_content"]).decode("ascii")
        data["raw_content_is_b64"] = True
    return data


def deserialize_bronze(data: dict) -> BronzeRecord:
    data = dict(data)
    if data.pop("raw_content_is_b64", False):
        data["raw_content"] = base64.b64decode(data["raw_content"])
    return BronzeRecord(**data)


def serialize_silver(record: SilverRecord) -> dict:
    return asdict(record)


def deserialize_silver(data: dict) -> SilverRecord:
    return SilverRecord(**data)


def serialize_eval_result(result: EvalResult) -> dict:
    return asdict(result)


def deserialize_eval_result(data: dict) -> EvalResult:
    return EvalResult(**data)
