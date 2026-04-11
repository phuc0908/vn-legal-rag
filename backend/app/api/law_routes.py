from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.db.database import query_all, query_one

router = APIRouter(prefix="/law", tags=["law"])


@router.get("/stats")
def get_stats():
    """Database statistics"""
    chude_count = query_one("SELECT COUNT(*) as cnt FROM pdchude")["cnt"]
    demuc_count = query_one("SELECT COUNT(*) as cnt FROM pddemuc")["cnt"]
    chuong_count = query_one("SELECT COUNT(*) as cnt FROM pdchuong")["cnt"]
    dieu_count = query_one("SELECT COUNT(*) as cnt FROM pddieu")["cnt"]
    return {
        "chude": chude_count,
        "demuc": demuc_count,
        "chuong": chuong_count,
        "dieu": dieu_count,
    }


@router.get("/chude")
def list_chude():
    """List all chủ đề (law topics)"""
    rows = query_all("SELECT id, ten, stt FROM pdchude ORDER BY stt")
    return rows


@router.get("/demuc")
def list_demuc(chude_id: str = Query(..., description="ID of chủ đề")):
    """List đề mục for a chủ đề"""
    rows = query_all(
        "SELECT id, ten, stt FROM pddemuc WHERE chude_id = %s ORDER BY stt",
        (chude_id,),
    )
    return rows


@router.get("/chuong")
def list_chuong(demuc_id: str = Query(..., description="ID of đề mục")):
    """List chương for an đề mục"""
    rows = query_all(
        "SELECT mapc, ten, chimuc, stt FROM pdchuong WHERE demuc_id = %s ORDER BY stt",
        (demuc_id,),
    )
    return rows


@router.get("/dieu/list")
def list_dieu(
    chuong_id: Optional[str] = Query(None, description="ID of chương"),
    demuc_id: Optional[str] = Query(None, description="ID of đề mục"),
):
    """List điều (articles) for a chương or đề mục.

    Mỗi item có thêm trường `is_muc` (bool):
    - True  → đây là dòng tiêu đề Mục (Mục 1, Mục 2...), dùng để nhóm các điều bên dưới
    - False → điều luật thông thường
    """
    if chuong_id:
        rows = query_all(
            "SELECT mapc, ten, chimuc, stt, vbqppl FROM pddieu WHERE chuong_id = %s ORDER BY stt",
            (chuong_id,),
        )
    elif demuc_id:
        rows = query_all(
            "SELECT mapc, ten, chimuc, stt, vbqppl FROM pddieu WHERE demuc_id = %s ORDER BY stt",
            (demuc_id,),
        )
    else:
        raise HTTPException(status_code=400, detail="Cần cung cấp chuong_id hoặc demuc_id")

    for row in rows:
        row["is_muc"] = row["mapc"].endswith("0000000000000000")

    return rows


@router.get("/dieu/{mapc:path}")
def get_dieu(mapc: str):
    """Get full detail of a điều (article)"""
    dieu = query_one(
        """
        SELECT d.mapc, d.ten, d.chimuc, d.stt, d.noidung, d.vbqppl, d.vbqppl_link,
               d.demuc_id, d.chuong_id, d.chude_id,
               c.ten as chuong_ten, c.chimuc as chuong_chimuc,
               dm.ten as demuc_ten,
               cd.ten as chude_ten
        FROM pddieu d
        LEFT JOIN pdchuong c ON d.chuong_id = c.mapc
        LEFT JOIN pddemuc dm ON d.demuc_id = dm.id
        LEFT JOIN pdchude cd ON d.chude_id = cd.id
        WHERE d.mapc = %s
        """,
        (mapc,),
    )
    if not dieu:
        raise HTTPException(status_code=404, detail="Không tìm thấy điều luật")

    try:
        tables = query_all("SELECT id, html FROM pdtable WHERE dieu_id = %s", (mapc,))
    except Exception:
        tables = []

    try:
        files = query_all("SELECT id, link, path FROM pdfile WHERE dieu_id = %s", (mapc,))
    except Exception:
        files = []

    try:
        related = query_all(
            """
            SELECT r.dieu_id2_id as mapc, d.ten, d.vbqppl
            FROM pdmuclienquan r
            JOIN pddieu d ON r.dieu_id2_id = d.mapc
            WHERE r.dieu_id1_id = %s
            LIMIT 10
            """,
            (mapc,),
        )
    except Exception:
        related = []

    return {
        **dieu,
        "tables": tables,
        "files": files,
        "related": related,
    }


@router.get("/search")
def search_dieu(
    q: str = Query(..., min_length=1, description="Search keyword"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Search điều by keyword in ten or noidung"""
    offset = (page - 1) * size
    keyword = f"%{q}%"

    total_row = query_one(
        "SELECT COUNT(*) as cnt FROM pddieu WHERE ten LIKE %s OR noidung LIKE %s",
        (keyword, keyword),
    )
    total = total_row["cnt"] if total_row else 0

    rows = query_all(
        """
        SELECT d.mapc, d.ten, d.chimuc, d.vbqppl,
               LEFT(d.noidung, 300) as noidung_preview,
               cd.ten as chude_ten, dm.ten as demuc_ten
        FROM pddieu d
        LEFT JOIN pdchude cd ON d.chude_id = cd.id
        LEFT JOIN pddemuc dm ON d.demuc_id = dm.id
        WHERE d.ten LIKE %s OR d.noidung LIKE %s
        ORDER BY d.chude_id, d.stt
        LIMIT %s OFFSET %s
        """,
        (keyword, keyword, size, offset),
    )

    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
        "results": rows,
    }
