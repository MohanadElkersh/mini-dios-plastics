"""Session fixtures for Mini-DIOS Plastics pytest suite."""
from __future__ import annotations

import pytest

from core.ontology import PlantDataset, SolveResult
from core.seed import default_config, demo_dataset
from core.solver import solve_plant_schedule


@pytest.fixture(scope="session")
def base_plant_dataset() -> PlantDataset:
    return demo_dataset()


@pytest.fixture(scope="session")
def base_solve_result(base_plant_dataset: PlantDataset) -> SolveResult:
    return solve_plant_schedule(base_plant_dataset, default_config())
