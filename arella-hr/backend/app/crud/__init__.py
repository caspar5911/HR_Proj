# CRUD operations live in dedicated files per model
from app.crud.department import (  # noqa: F401
    get_department,
    list_departments,
    create_department,
    update_department,
    delete_department,
)
from app.crud.leave_type import (  # noqa: F401
    get_leave_type,
    list_leave_types,
    create_leave_type,
    update_leave_type,
    delete_leave_type,
)
from app.crud.leave_balance import (  # noqa: F401
    get_leave_balance,
    list_leave_balances,
    create_leave_balance,
    add_used_days,
    remove_used_days,
)
from app.crud.leave_request import (  # noqa: F401
    get_leave_request,
    list_leave_requests,
    create_leave_request,
    approve_leave_request,
    reject_leave_request,
    cancel_leave_request,
)
from app.crud.payroll_run import (  # noqa: F401
    get_payroll_run,
    list_payroll_runs,
    create_payroll_run,
    update_payroll_run,
    delete_payroll_run,
    list_payroll_entries,
    get_payroll_entry,
)
from app.crud.deduction_rule import (  # noqa: F401
    get_deduction_rule,
    list_deduction_rules,
    create_deduction_rule,
    update_deduction_rule,
    delete_deduction_rule,
)