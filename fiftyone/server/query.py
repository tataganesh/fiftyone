"""
FiftyOne Server queries

| Copyright 2017-2022, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import typing as t
from datetime import date, datetime
from enum import Enum
import os

import eta.core.serial as etas
import strawberry as gql
from bson import ObjectId
from dacite import Config, from_dict


import fiftyone as fo
import fiftyone.constants as foc
import fiftyone.core.context as focx
import fiftyone.core.uid as fou

from fiftyone.server.data import Info
from fiftyone.server.dataloader import get_dataloader_resolver
from fiftyone.server.mixins import HasCollection
from fiftyone.server.paginator import Connection, get_paginator_resolver

ID = gql.scalar(
    t.NewType("ID", str),
    serialize=lambda v: str(v),
    parse_value=lambda v: ObjectId(v),
)
DATASET_FILTER = [{"sample_collection_name": {"$regex": "^samples\\."}}]
DATASET_FILTER_STAGE = [{"$match": DATASET_FILTER[0]}]


@gql.enum
class MediaType(Enum):
    image = "image"
    video = "video"


@gql.type
class Target:
    target: int
    value: str


@gql.type
class NamedTargets:
    name: str
    targets: t.List[Target]


@gql.type
class SampleField:
    ftype: str
    path: str
    subfield: t.Optional[str]
    embedded_doc_type: t.Optional[str]
    db_field: t.Optional[str]


@gql.interface
class RunConfig:
    cls: str


@gql.interface
class Run:
    key: str
    version: str
    timestamp: datetime
    config: RunConfig
    view_stages: t.List[str]


@gql.type
class BrainRunConfig(RunConfig):
    embeddings_field: t.Optional[str]
    method: str
    patches_field: t.Optional[str]


@gql.type
class BrainRun(Run):
    config: BrainRunConfig


@gql.type
class EvaluationRunConfig(RunConfig):
    classwise: bool
    error_level: int
    gt_field: str
    pred_field: str
    method: str


@gql.type
class EvaluationRun(Run):
    config: EvaluationRunConfig


@gql.type
class SidebarGroup:
    name: str
    paths: t.List[str]


@gql.type
class Dataset(HasCollection):
    id: gql.ID
    name: str
    created_at: date
    last_loaded_at: datetime
    persistent: bool
    media_type: t.Optional[MediaType]
    mask_targets: t.List[NamedTargets]
    default_mask_targets: t.Optional[t.List[Target]]
    sample_fields: t.List[SampleField]
    frame_fields: t.List[SampleField]
    brain_methods: t.List[BrainRun]
    evaluations: t.List[EvaluationRun]
    app_sidebar_groups: t.Optional[t.List[SidebarGroup]]
    version: str

    @staticmethod
    def get_collection_name() -> str:
        return "datasets"

    @staticmethod
    def modifier(doc: dict) -> dict:

        doc["id"] = doc.pop("_id")
        doc["mask_targets"] = []
        doc["default_mask_targets"] = []
        doc["sample_fields"] = _flatten_fields([], doc["sample_fields"])
        doc["frame_fields"] = _flatten_fields([], doc["frame_fields"])
        doc["brain_methods"] = list(doc.get("brain_methods", {}).values())
        doc["evaluations"] = list(doc.get("evaluations", {}).values())
        return doc

    @classmethod
    async def resolver(cls, name: str, info: Info) -> t.Optional["Dataset"]:
        return await dataset_dataloader(name, info)


dataset_dataloader = get_dataloader_resolver(Dataset, "name", DATASET_FILTER)


@gql.type
class AppConfig:
    timezone: t.Optional[str]
    colorscale: str
    color_pool: t.List[str]
    grid_zoom: int
    loop_videos: bool
    notebook_height: int
    show_confidence: bool
    show_index: bool
    show_label: bool
    show_tooltip: bool
    use_frame_number: bool


@gql.type
class Query:
    @gql.field
    def colorscale(self) -> t.Optional[t.List[t.List[int]]]:
        if fo.app_config.colorscale:
            return fo.app_config.get_colormap()

        return None

    @gql.field
    def config(self) -> AppConfig:
        d = fo.app_config.serialize()
        d["timezone"] = fo.config.timezone
        return from_dict(AppConfig, d, config=Config(check_types=False))

    @gql.field
    def context(self) -> str:
        return focx._get_context()

    @gql.field
    def dev(self) -> bool:
        return foc.DEV_INSTALL or foc.RC_INSTALL

    @gql.field
    def do_not_track(self) -> bool:
        return fo.config.do_not_track

    dataset = gql.field(resolver=Dataset.resolver)
    datasets: Connection[Dataset] = gql.field(
        resolver=get_paginator_resolver(
            Dataset,
            "created_at",
            DATASET_FILTER_STAGE,
        )
    )

    @gql.field
    def teams_submission(self) -> bool:
        isfile = os.path.isfile(foc.TEAMS_PATH)
        if isfile:
            submitted = etas.load_json(foc.TEAMS_PATH)["submitted"]
        else:
            submitted = False

        return submitted

    @gql.field
    def uuid(self) -> str:
        uid, _ = fou.get_user_id()
        return uid

    @gql.field
    def version(self) -> str:
        return foc.VERSION


def _flatten_fields(path, fields):
    result = []
    for field in fields:
        key = field.pop("name")
        field_path = path + [key]
        field["path"] = ".".join(field_path)
        result.append(field)

        fields = field.pop("fields", None)
        if fields:
            result = result + _flatten_fields(field_path, fields)

    return result
