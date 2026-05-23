import os
import sys
import calendar as cal_module
from datetime import date, datetime

from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import init_db
from models.teacher import Teacher
from models.school_class import Class
from models.subject import Subject
from models.schedule import Schedule

app = FastAPI(title="Школьное расписание")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

MONTH_NAMES = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
               "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
MONTH_GEN = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
             "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
STATUSES = [
    ("работает",   "Работает"),
    ("на замене",  "На замене"),
    ("болеет",     "Болеет"),
    ("отсутствует","Отсутствует"),
]


@app.on_event("startup")
def on_startup():
    init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def prev_next(year, month):
    pm, py = (month - 1, year) if month > 1 else (12, year - 1)
    nm, ny = (month + 1, year) if month < 12 else (1, year + 1)
    return py, pm, ny, nm


def build_calendar(teacher_id, year, month):
    """Возвращает список недель; каждая ячейка — dict с данными или None."""
    counts = Schedule.get_daily_lesson_counts_for_teacher_month(teacher_id, year, month)
    today = date.today()
    result = []
    for week in cal_module.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(None)
            else:
                ds = f"{year}-{month:02d}-{day:02d}"
                row.append({
                    "day": day,
                    "date_str": ds,
                    "count": counts.get(ds, 0),
                    "is_today": (year == today.year and month == today.month and day == today.day),
                    "is_weekend": False,  # будет установлен по позиции в неделе
                })
        # суббота/воскресенье
        for i, cell in enumerate(row):
            if cell:
                cell["is_weekend"] = (i >= 5)
        result.append(row)
    return result


def teacher_month_info(teacher, year, month):
    last = cal_module.monthrange(year, month)[1]
    scheds = Schedule.get_by_teacher_date_range(
        teacher.id, f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last}"
    )
    c = {"работает": 0, "на замене": 0, "болеет": 0, "отсутствует": 0}
    for s in scheds:
        k = s.status or "работает"
        c[k] = c.get(k, 0) + 1
    hours = c["работает"] + c["на замене"]
    diff = hours - int(teacher.rate)
    return {"hours": hours, "rate": int(teacher.rate), "diff": diff, "counts": c}


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse("/schedule")


# ── Schedule ──────────────────────────────────────────────────────────────────

@app.get("/schedule", response_class=HTMLResponse)
async def schedule_index(request: Request):
    today = date.today()
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "teachers": Teacher.get_all(),
        "selected": None,
        "year": today.year, "month": today.month,
        "month_name": f"{MONTH_NAMES[today.month]} {today.year}",
        "weeks": [], "weekdays": WEEKDAYS,
        "teacher_info": None,
        "prev_year": None, "prev_month": None,
        "next_year": None, "next_month": None,
    })


@app.get("/schedule/{teacher_id}/{year}/{month}", response_class=HTMLResponse)
async def schedule_teacher(request: Request, teacher_id: int, year: int, month: int):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        return RedirectResponse("/schedule")
    py, pm, ny, nm = prev_next(year, month)
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "teachers": Teacher.get_all(),
        "selected": teacher,
        "year": year, "month": month,
        "month_name": f"{MONTH_NAMES[month]} {year}",
        "weeks": build_calendar(teacher_id, year, month),
        "weekdays": WEEKDAYS,
        "teacher_info": teacher_month_info(teacher, year, month),
        "prev_year": py, "prev_month": pm,
        "next_year": ny, "next_month": nm,
    })


@app.get("/schedule/{teacher_id}/day/{date_str}", response_class=HTMLResponse)
async def day_get(request: Request, teacher_id: int, date_str: str):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        return RedirectResponse("/schedule")
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return RedirectResponse("/schedule")

    existing = {s.lesson_number: s
                for s in Schedule.get_by_date_and_teacher(date_str, teacher_id)}
    return templates.TemplateResponse("day_schedule.html", {
        "request": request,
        "teacher": teacher,
        "date_str": date_str,
        "date_display": f"{d.day} {MONTH_GEN[d.month]} {d.year}",
        "year": d.year, "month": d.month,
        "subjects": Subject.get_all(),
        "classes": Class.get_all(),
        "lessons": existing,
        "statuses": STATUSES,
        "nums": range(1, 9),
        "error": None,
    })


@app.post("/schedule/{teacher_id}/day/{date_str}", response_class=HTMLResponse)
async def day_post(request: Request, teacher_id: int, date_str: str):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        return RedirectResponse("/schedule")
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return RedirectResponse("/schedule")

    form = await request.form()

    # Удаляем старые уроки этого дня
    for s in Schedule.get_by_date_and_teacher(date_str, teacher_id):
        s.delete()

    errors = []
    for i in range(1, 9):
        raw_s = form.get(f"subject_{i}", "0")
        raw_c = form.get(f"class_{i}", "0")
        status = form.get(f"status_{i}", "работает")
        if raw_s == "0" or raw_c == "0":
            continue
        subj_id, cls_id = int(raw_s), int(raw_c)

        conflict = Schedule.get_conflicting_class_entry(cls_id, date_str, i)
        if conflict and conflict[1] != teacher_id:
            ct = Teacher.get_by_id(conflict[1])
            cls = Class.get_by_id(cls_id)
            errors.append(
                f"Урок {i}: класс «{cls.name if cls else cls_id}» "
                f"уже занят у {ct.name if ct else '?'}"
            )
            continue

        Schedule(teacher_id=teacher_id, class_id=cls_id,
                 subject_id=subj_id, date=date_str,
                 lesson_number=i, status=status).save()

    if errors:
        existing = {s.lesson_number: s
                    for s in Schedule.get_by_date_and_teacher(date_str, teacher_id)}
        return templates.TemplateResponse("day_schedule.html", {
            "request": request,
            "teacher": teacher,
            "date_str": date_str,
            "date_display": f"{d.day} {MONTH_GEN[d.month]} {d.year}",
            "year": d.year, "month": d.month,
            "subjects": Subject.get_all(),
            "classes": Class.get_all(),
            "lessons": existing,
            "statuses": STATUSES,
            "nums": range(1, 9),
            "error": " | ".join(errors),
        })

    return RedirectResponse(f"/schedule/{teacher_id}/{d.year}/{d.month}", status_code=303)


# ── Teachers ──────────────────────────────────────────────────────────────────

@app.get("/teachers", response_class=HTMLResponse)
async def teachers_list(request: Request, error: str = None, success: str = None):
    today = date.today()
    data = [{"teacher": t, "info": teacher_month_info(t, today.year, today.month)}
            for t in Teacher.get_all()]
    return templates.TemplateResponse("teachers.html", {
        "request": request,
        "teachers_data": data,
        "month_name": MONTH_NAMES[today.month],
        "error": error, "success": success,
    })


@app.post("/teachers/add", response_class=HTMLResponse)
async def teacher_add(request: Request):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        return RedirectResponse("/teachers?error=Введите+ФИО+учителя", status_code=303)
    spec = [s.strip() for s in form.get("specialization", "").split(",") if s.strip()]
    rate = int(form.get("rate") or 18)
    Teacher(name=name, specialization=spec, rate=rate).save()
    return RedirectResponse("/teachers?success=Учитель+добавлен", status_code=303)


@app.get("/teachers/{teacher_id}/edit", response_class=HTMLResponse)
async def teacher_edit_get(request: Request, teacher_id: int):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        return RedirectResponse("/teachers")
    return templates.TemplateResponse("teacher_edit.html", {
        "request": request, "teacher": teacher, "error": None,
    })


@app.post("/teachers/{teacher_id}/edit", response_class=HTMLResponse)
async def teacher_edit_post(request: Request, teacher_id: int):
    teacher = Teacher.get_by_id(teacher_id)
    if not teacher:
        return RedirectResponse("/teachers")
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        return templates.TemplateResponse("teacher_edit.html", {
            "request": request, "teacher": teacher, "error": "Введите ФИО учителя",
        })
    teacher.name = name
    teacher.specialization = [s.strip() for s in form.get("specialization", "").split(",") if s.strip()]
    teacher.rate = int(form.get("rate") or 18)
    teacher.save()
    return RedirectResponse("/teachers?success=Данные+сохранены", status_code=303)


@app.post("/teachers/{teacher_id}/delete", response_class=HTMLResponse)
async def teacher_delete(teacher_id: int):
    teacher = Teacher.get_by_id(teacher_id)
    if teacher:
        teacher.delete()
    return RedirectResponse("/teachers?success=Учитель+удалён", status_code=303)


# ── Classes ───────────────────────────────────────────────────────────────────

@app.get("/classes", response_class=HTMLResponse)
async def classes_list(request: Request, error: str = None, success: str = None):
    return templates.TemplateResponse("classes.html", {
        "request": request, "classes": Class.get_all(),
        "error": error, "success": success,
    })


@app.post("/classes/add", response_class=HTMLResponse)
async def class_add(request: Request):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        return RedirectResponse("/classes?error=Введите+название+класса", status_code=303)
    Class(name=name).save()
    return RedirectResponse("/classes?success=Класс+добавлен", status_code=303)


@app.post("/classes/{class_id}/delete", response_class=HTMLResponse)
async def class_delete(class_id: int):
    cls = Class.get_by_id(class_id)
    if not cls:
        return RedirectResponse("/classes")
    if Schedule.get_by_class(cls.id):
        return RedirectResponse(
            "/classes?error=Нельзя+удалить+класс+используемый+в+расписании",
            status_code=303)
    cls.delete()
    return RedirectResponse("/classes?success=Класс+удалён", status_code=303)


# ── Subjects ──────────────────────────────────────────────────────────────────

@app.get("/subjects", response_class=HTMLResponse)
async def subjects_list(request: Request, error: str = None, success: str = None):
    return templates.TemplateResponse("subjects.html", {
        "request": request, "subjects": Subject.get_all(),
        "error": error, "success": success,
    })


@app.post("/subjects/add", response_class=HTMLResponse)
async def subject_add(request: Request):
    form = await request.form()
    name = form.get("name", "").strip()
    if not name:
        return RedirectResponse("/subjects?error=Введите+название+предмета", status_code=303)
    Subject(name=name).save()
    return RedirectResponse("/subjects?success=Предмет+добавлен", status_code=303)


@app.post("/subjects/{subject_id}/delete", response_class=HTMLResponse)
async def subject_delete(subject_id: int):
    subj = Subject.get_by_id(subject_id)
    if not subj:
        return RedirectResponse("/subjects")
    if Schedule.get_by_subject(subj.id):
        return RedirectResponse(
            "/subjects?error=Нельзя+удалить+предмет+используемый+в+расписании",
            status_code=303)
    subj.delete()
    return RedirectResponse("/subjects?success=Предмет+удалён", status_code=303)


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)
