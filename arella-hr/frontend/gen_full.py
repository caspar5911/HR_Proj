"""Generate the full employees.tsx page."""
import os
import sys

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "routes", "employees.tsx")
print(f"Generating: {out}")

Q = chr(34)  # double quote
BS = chr(92)  # backslash

lines = []
def w(s=""):
    lines.append(s)


# ============ IMPORTS ============
w(f"import {{ useState, useMemo, useCallback }} from {Q}react{Q};")
w(f"import {{ useQuery, useMutation, useQueryClient }} from {Q}@tanstack/react-query{Q};")
w(f"import {{ useAuth }} from {Q}@/lib/auth{Q};")
w(f"import {{")
w(f"  listEmployees,")
w(f"  createEmployee,")
w(f"  updateEmployee,")
w(f"  deactivateEmployee,")
w(f"  restoreEmployee,")
w(f"  deleteEmployee,")
w(f"  type Employee,")
w(f"  type EmployeeCreate,")
w(f"  type EmployeeUpdate,")
w(f"}} from {Q}@/lib/employee{Q};")
w(f"import {{")
w(f"  Table,")
w(f"  TableBody,")
w(f"  TableCell,")
w(f"  TableHead,")
w(f"  TableHeader,")
w(f"  TableRow,")
w(f"}} from {Q}@/components/ui/table{Q};")
w(f"import {{ Badge }} from {Q}@/components/ui/badge{Q};")
w(f"import {{ Button }} from {Q}@/components/ui/button{Q};")
w(f"import {{")
w(f"  Dialog,")
w(f"  DialogContent,")
w(f"  DialogHeader,")
w(f"  DialogTitle,")
w(f"  DialogFooter,")
w(f"  DialogClose,")
w(f"}} from {Q}@/components/ui/dialog{Q};")
w(f"import {{ Input }} from {Q}@/components/ui/input{Q};")
w(f"import {{ Label }} from {Q}@/components/ui/label{Q};")
w(f"import {{ Card, CardContent }} from {Q}@/components/ui/card{Q};")

