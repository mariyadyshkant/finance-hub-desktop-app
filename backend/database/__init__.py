# database.py era un unico file da 666 righe con le query di ogni dominio
# (transazioni, rimborsi, risparmi, turni, budget, categorie...) — separato
# per dominio come già fatto per routes/ (issue-audit-2). Questo __init__
# riesporta tutto così il resto del backend continua a fare
# `import database as db` / `db.get_transactions(...)` senza modifiche.

from .connection import (
    DB_PATH,
    TURSO_URL,
    TURSO_TOKEN,
    get_conn,
    db_backend_label,
    init_db,
)

from .transactions import (
    get_transactions,
    add_transaction,
    update_transaction,
    delete_transaction,
    import_transactions_bulk,
    get_available_months,
)

from .reimbursements import (
    get_reimbursements,
    add_reimbursement,
    update_reimbursement,
    delete_reimbursement,
)

from .savings import (
    get_savings,
    add_savings_entry,
    delete_savings_entry,
)

from .shifts import (
    get_shifts,
    add_shift,
    delete_shift,
    add_shifts_bulk,
)

from .salary import (
    get_salary_records,
    add_salary_record,
    delete_salary_record,
)

from .budgets import (
    get_budgets,
    set_budget,
)

from .summaries import (
    init_monthly_summaries,
    upsert_monthly_summary,
    get_monthly_summaries,
    get_summary_months,
    delete_monthly_summary_month,
)

from .planning import (
    get_monthly_budget,
    upsert_monthly_budget,
    init_planned_expenses,
    get_planned_expenses,
    add_planned_expense,
    update_planned_expense,
    delete_planned_expense,
    get_overrides,
    upsert_override,
    delete_override,
)

from .settings import (
    init_settings,
    get_setting,
    set_setting,
)

from .categories import (
    init_categories,
    get_categories,
    add_category,
    set_category_color,
    set_category_icon,
    rename_category,
    delete_category,
)
