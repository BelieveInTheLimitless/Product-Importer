from fastapi import APIRouter, UploadFile, File, HTTPException
from celery.result import AsyncResult
from app.tasks.celery_app import celery
from app.services.storage import save_csv

router = APIRouter()

@router.post("/", status_code=200)
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")

    path = save_csv(file)

    task = celery.send_task("app.tasks.import_task.import_csv_task", args=[path])

    return {"task_id": task.id}

@router.get("/status/{task_id}")
def get_status(task_id: str):
    try:
        res = AsyncResult(task_id, app=celery)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Celery error: {str(e)}")

    try:
        status = res.status
        result = res.result
    except Exception as e:
        return {"task_id": task_id, "status": "UNKNOWN", "detail": "Unable to read result from backend", "error": str(e)}

    return {"task_id": task_id, "status": status, "result": result}