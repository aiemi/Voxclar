from fastapi import APIRouter

router = APIRouter()


@router.get("/{transcript_id}")
async def get_transcript(transcript_id: str):
    return {"message": "Transcript endpoint", "id": transcript_id}
