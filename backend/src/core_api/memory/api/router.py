"""HTTP API for the memory bounded context.

Every endpoint operates on "my memory" — scoped to the caller's
authenticated identity, same convention as every other module.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from core_api.decisions.domain.exceptions import DecisionNotFoundError
from core_api.decisions.domain.repositories import DecisionRepository
from core_api.dependencies import (
    get_current_identity,
    get_decision_repository,
    get_memory_embedding_repository,
    get_user_bias_profile_repository,
)
from core_api.identity.application.use_cases import AuthenticatedIdentity
from core_api.memory.api.schemas import (
    BiasObservationResponse,
    FindSimilarMemoriesRequest,
    MemoryResponse,
    RecordBiasObservationRequest,
    RecordCalibrationRequest,
    StoreMemoryRequest,
    UserBiasProfileResponse,
)
from core_api.memory.application.use_cases import (
    FindSimilarMemoriesInput,
    FindSimilarMemoriesUseCase,
    GetUserBiasProfileUseCase,
    ListMemoriesForUserUseCase,
    RecordBiasObservationInput,
    RecordBiasObservationUseCase,
    RecordCalibrationInput,
    RecordCalibrationUseCase,
    StoreMemoryInput,
    StoreMemoryUseCase,
)
from core_api.memory.domain.entities import MemoryEmbedding, UserBiasProfile
from core_api.memory.domain.repositories import MemoryEmbeddingRepository, UserBiasProfileRepository

router = APIRouter(prefix="/v1/memory", tags=["memory"])

_MemoryRepo = Annotated[MemoryEmbeddingRepository, Depends(get_memory_embedding_repository)]


def _to_profile_response(profile: UserBiasProfile) -> UserBiasProfileResponse:
    return UserBiasProfileResponse(
        biases=[
            BiasObservationResponse(bias=b.bias, score=b.score, occurrences=b.occurrences)
            for b in profile.biases
        ],
        calibration_score=profile.calibration_score,
        updated_at=profile.updated_at,
    )


def _to_memory_response(memory: MemoryEmbedding, similarity: float | None = None) -> MemoryResponse:
    return MemoryResponse(
        id=memory.id,
        decision_id=memory.decision_id,
        summary_text=memory.summary_text,
        created_at=memory.created_at,
        similarity=similarity,
    )


@router.get("/bias-profile", response_model=UserBiasProfileResponse)
async def get_bias_profile(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    profile_repository: Annotated[
        UserBiasProfileRepository, Depends(get_user_bias_profile_repository)
    ],
) -> UserBiasProfileResponse:
    profile = await GetUserBiasProfileUseCase(profile_repository).execute(identity.id)
    return _to_profile_response(profile)


@router.post("/bias-observations", response_model=UserBiasProfileResponse)
async def record_bias_observation(
    payload: RecordBiasObservationRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    profile_repository: Annotated[
        UserBiasProfileRepository, Depends(get_user_bias_profile_repository)
    ],
) -> UserBiasProfileResponse:
    profile = await RecordBiasObservationUseCase(profile_repository).execute(
        RecordBiasObservationInput(
            user_id=identity.id, bias=payload.bias, confidence=payload.confidence
        )
    )
    return _to_profile_response(profile)


@router.post("/calibration", response_model=UserBiasProfileResponse)
async def record_calibration(
    payload: RecordCalibrationRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    profile_repository: Annotated[
        UserBiasProfileRepository, Depends(get_user_bias_profile_repository)
    ],
) -> UserBiasProfileResponse:
    profile = await RecordCalibrationUseCase(profile_repository).execute(
        RecordCalibrationInput(user_id=identity.id, calibration_delta=payload.calibration_delta)
    )
    return _to_profile_response(profile)


@router.get("/embeddings", response_model=list[MemoryResponse])
async def list_memories(
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    memory_repository: _MemoryRepo,
) -> list[MemoryResponse]:
    memories = await ListMemoriesForUserUseCase(memory_repository).execute(identity.id)
    return [_to_memory_response(m) for m in memories]


@router.post("/embeddings", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def store_memory(
    payload: StoreMemoryRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    memory_repository: _MemoryRepo,
    decision_repository: Annotated[DecisionRepository, Depends(get_decision_repository)],
) -> MemoryResponse:
    try:
        memory = await StoreMemoryUseCase(memory_repository, decision_repository).execute(
            StoreMemoryInput(
                user_id=identity.id,
                summary_text=payload.summary_text,
                embedding=tuple(payload.embedding),
                decision_id=payload.decision_id,
            )
        )
    except DecisionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found"
        ) from exc
    return _to_memory_response(memory)


@router.post("/embeddings/search", response_model=list[MemoryResponse])
async def search_memories(
    payload: FindSimilarMemoriesRequest,
    identity: Annotated[AuthenticatedIdentity, Depends(get_current_identity)],
    memory_repository: _MemoryRepo,
) -> list[MemoryResponse]:
    results = await FindSimilarMemoriesUseCase(memory_repository).execute(
        FindSimilarMemoriesInput(
            user_id=identity.id, query_embedding=tuple(payload.embedding), top_k=payload.top_k
        )
    )
    return [_to_memory_response(memory, similarity) for memory, similarity in results]
