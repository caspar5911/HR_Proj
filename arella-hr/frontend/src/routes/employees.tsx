import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/lib/auth";
import {
  listEmployees, createEmployee, updateEmployee,
  deactivateEmployee, restoreEmployee, deleteEmployee,
  type Employee, type EmployeeCreate, type EmployeeUpdate,
} from "@/lib/employee";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogClose } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, Search, Edit, Trash2, PowerOff, Check, Calendar, Users } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { toast } from "@/hooks/use-toast";

interface EmployeeFormValues {
  first_name: string; last_name: string; email: string; phone: string;
  department: string; position: string; hire_date: string; salary_base: string;
  address: string; manager_id: string;
  status: "active" | "inactive" | "on_leave";
}

function statusVariant(s: string): "default"|"secondary"|"destructive"|"outline" {
  if (s === "active") return "default";
  if (s === "inactive") return "destructive";
  if (s === "on_leave") return "secondary";
  return "outline";
}

function formatDate(d: string | null): string {
  if (!d) return "—";
  try { return new Date(d).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  catch { return "—"; }
}

function formatSalary(v: number | null): string {
  if (v == null) return "—";
  return "$" + v.toLocaleString("en-US");
}

const DEPT_OPTIONS = ["Engineering", "Design", "Marketing", "Sales", "HR", "Finance"];

function EmployeeFormDialog({ open, onOpenChange, employee, onSubmit }: {
  open: boolean; onOpenChange: (o: boolean) => void;
  employee: Employee | null; onSubmit: (d: EmployeeCreate | EmployeeUpdate) => void;
}) {
  const [form, setForm] = useState<EmployeeFormValues>({
    first_name: employee?.first_name ?? "", last_name: employee?.last_name ?? "",
    email: employee?.email ?? "", phone: employee?.phone ?? "",
    department: employee?.department ?? "", position: employee?.position ?? "",
    hire_date: employee?.hire_date ? employee.hire_date.split("T")[0] : "",
    salary_base: employee?.salary_base?.toString() ?? "",
    address: employee?.address ?? "", manager_id: employee?.manager_id?.toString() ?? "",
    status: employee?.status ?? "active",
  });
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const d: Record<string, unknown> = { ...form };
    if (form.salary_base) d.salary_base = Number(form.salary_base);
    if (form.manager_id) d.manager_id = Number(form.manager_id);
    if (!d.phone) delete d.phone;
    if (!d.department) delete d.department;
    if (!d.position) delete d.position;
    if (!d.address) delete d.address;
    if (!d.hire_date) delete d.hire_date;
    onSubmit(d as EmployeeCreate | EmployeeUpdate);
    if (!employee) setForm({ first_name: "", last_name: "", email: "", phone: "", department: "", position: "", hire_date: "", salary_base: "", address: "", manager_id: "", status: "active" });
  };
  const upd = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));
  const depts = DEPT_OPTIONS;
  const statuses: EmployeeFormValues["status"][] = ["active", "inactive", "on_leave"];
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader><DialogTitle>{employee ? "Edit Employee" : "Add Employee"}</DialogTitle></DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label htmlFor="fn">First Name</Label><Input id="fn" value={form.first_name} onChange={(e) => upd("first_name", e.target.value)} required placeholder="Jane" /></div>
            <div className="space-y-2"><Label htmlFor="ln">Last Name</Label><Input id="ln" value={form.last_name} onChange={(e) => upd("last_name", e.target.value)} required placeholder="Doe" /></div>
          </div>
          <div className="space-y-2"><Label htmlFor="em">Email</Label><Input id="em" type="email" value={form.email} onChange={(e) => upd("email", e.target.value)} required placeholder="jane.doe@company.com" /></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label htmlFor="ph">Phone</Label><Input id="ph" value={form.phone} onChange={(e) => upd("phone", e.target.value)} placeholder="+1 555-123-4567" /></div>
            <div className="space-y-2"><Label htmlFor="dp">Department</Label><Select value={form.department} onValueChange={(v) => upd("department", v)}><SelectTrigger id="dp"><SelectValue placeholder="Select" /></SelectTrigger><SelectContent><SelectItem value="">No Department</SelectItem>{depts.map((d) => (<SelectItem key={d} value={d}>{d}</SelectItem>))}</SelectContent></Select></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label htmlFor="po">Position</Label><Input id="po" value={form.position} onChange={(e) => upd("position", e.target.value)} placeholder="Software Engineer" /></div>
            <div className="space-y-2"><Label htmlFor="hd">Hire Date</Label><Input id="hd" type="date" value={form.hire_date} onChange={(e) => upd("hire_date", e.target.value)} /></div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label htmlFor="sb">Base Salary</Label><Input id="sb" type="number" value={form.salary_base} onChange={(e) => upd("salary_base", e.target.value)} placeholder="75000" /></div>
            <div className="space-y-2"><Label htmlFor="st">Status</Label><Select value={form.status} onValueChange={(v) => upd("status", v)}><SelectTrigger id="st"><SelectValue /></SelectTrigger><SelectContent>{statuses.map((s) => (<SelectItem key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</SelectItem>))}</SelectContent></Select></div>
          </div>
          <div className="space-y-2"><Label htmlFor="mi">Manager ID (optional)</Label><Input id="mi" type="number" value={form.manager_id} onChange={(e) => upd("manager_id", e.target.value)} placeholder="1" /></div>
          <div className="space-y-2"><Label htmlFor="ad">Address</Label><Input id="ad" value={form.address} onChange={(e) => upd("address", e.target.value)} placeholder="123 Main St, City, State" /></div>
          <DialogFooter>
            <DialogClose asChild><Button type="button" variant="outline">Cancel</Button></DialogClose>
            <Button type="submit">{employee ? "Save Changes" : "Add Employee"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}


export default function EmployeesPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isManager = isAdmin || user?.role === "manager";
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [debounced, setDebounced] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Employee | null>(null);
  const [confirmAction, setConfirmAction] = useState<null | { type: "deactivate"|"restore"|"delete"; employee: Employee }>(null);
  useEffect(() => { const t = setTimeout(() => setDebounced(search), 300); return () => clearTimeout(t); }, [search]);
  const { data, isLoading } = useQuery({
    queryKey: ["employees", { page, pageSize, search: debounced, department: deptFilter, status: statusFilter }],
    queryFn: async () => (await listEmployees({ page, page_size: pageSize, search: debounced || undefined, department: deptFilter || undefined, status: statusFilter || undefined, include_inactive: statusFilter === "inactive" || undefined })).data,
  });
  const mCreate = useMutation({ mutationFn: createEmployee, onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); setModalOpen(false); toast.success("Employee created successfully"); } });
  const mUpdate = useMutation({ mutationFn: ({ id, data }: { id: number; data: EmployeeUpdate }) => updateEmployee(id, data), onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); setModalOpen(false); setEditing(null); toast.success("Employee updated successfully"); } });
  const mDeactivate = useMutation({ mutationFn: deactivateEmployee, onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); setConfirmAction(null); toast.success("Employee deactivated"); } });
  const mRestore = useMutation({ mutationFn: restoreEmployee, onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); setConfirmAction(null); toast.success("Employee restored"); } });
  const mDelete = useMutation({ mutationFn: deleteEmployee, onSuccess: () => { qc.invalidateQueries({ queryKey: ["employees"] }); setConfirmAction(null); toast.success("Employee deleted"); } });

  const handleOpenAdd = () => { setEditing(null); setModalOpen(true); };
  const handleOpenEdit = (emp: Employee) => { setEditing(emp); setModalOpen(true); };
  const handleCreate = (d: EmployeeCreate) => mCreate.mutate(d);
  const handleUpdate = (d: EmployeeUpdate) => { if (editing) mUpdate.mutate({ id: editing.id, data: d }); };
  const handleConfirm = (action: "deactivate"|"restore"|"delete", emp: Employee) => setConfirmAction({ type: action, employee: emp });
  const handleExecute = () => {
    if (!confirmAction) return;
    const { type, employee } = confirmAction;
    if (type === "deactivate") mDeactivate.mutate(employee.id);
    else if (type === "restore") mRestore.mutate(employee.id);
    else if (type === "delete") mDelete.mutate(employee.id);
  };

  const emps = data?.items ?? [];
  const totalPages = data?.total_pages ?? 0;
  const totalEmp = data?.total ?? 0;
  const activeCount = emps.filter((e) => e.status === "active").length;
  const inactiveCount = emps.filter((e) => e.status === "inactive").length;
  const onLeaveCount = emps.filter((e) => e.status === "on_leave").length;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Employees</h1>
          <p className="text-muted-foreground mt-1">Manage your team members, departments, and roles.</p>
        </div>
        {isManager && <Button onClick={handleOpenAdd}><Plus className="h-4 w-4 mr-2" />Add Employee</Button>}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <Card><CardContent className="pt-6"><div className="flex items-center justify-between">
        <div><p className="text-sm text-muted-foreground">Total</p><p className="text-2xl font-bold">{totalEmp}</p></div>
        <div className="p-3 rounded-lg bg-blue-50"><Users className="h-5 w-5 text-blue-600" /></div>
      </div></CardContent></Card>
      <Card><CardContent className="pt-6"><div className="flex items-center justify-between">
        <div><p className="text-sm text-muted-foreground">Active</p><p className="text-2xl font-bold">{activeCount}</p></div>
        <div className="p-3 rounded-lg bg-green-50"><Check className="h-5 w-5 text-green-600" /></div>
      </div></CardContent></Card>
      <Card><CardContent className="pt-6"><div className="flex items-center justify-between">
        <div><p className="text-sm text-muted-foreground">Inactive</p><p className="text-2xl font-bold">{inactiveCount}</p></div>
        <div className="p-3 rounded-lg bg-red-50"><PowerOff className="h-5 w-5 text-red-600" /></div>
      </div></CardContent></Card>
      <Card><CardContent className="pt-6"><div className="flex items-center justify-between">
        <div><p className="text-sm text-muted-foreground">On Leave</p><p className="text-2xl font-bold">{onLeaveCount}</p></div>
        <div className="p-3 rounded-lg bg-amber-50"><Calendar className="h-5 w-5 text-amber-600" /></div>
      </div></CardContent></Card>
      </div>
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Search employees..." value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} className="pl-10" />
            </div>
            <Select value={deptFilter} onValueChange={(v) => { setDeptFilter(v); setPage(1); }}>
              <SelectTrigger className="w-full sm:w-[180px]"><SelectValue placeholder="All departments" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Departments</SelectItem>
                {DEPT_OPTIONS.map((d) => (<SelectItem key={d} value={d}>{d}</SelectItem>))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(1); }}>
              <SelectTrigger className="w-full sm:w-[160px]"><SelectValue placeholder="All statuses" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Statuses</SelectItem>
                <SelectItem value="active">Active</SelectItem>
                <SelectItem value="inactive">Inactive</SelectItem>
                <SelectItem value="on_leave">On Leave</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>
      <Card>
        <Table>
          <TableHeader><TableRow>
            <TableHead>Employee</TableHead>
            <TableHead>Department</TableHead>
            <TableHead>Position</TableHead>
            <TableHead className="hidden md:table-cell">Hire Date</TableHead>
            <TableHead className="hidden md:table-cell">Salary</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {isLoading && <TableRow><TableCell colSpan={7} className="text-center py-8 text-muted-foreground">Loading...</TableCell></TableRow>}
            {!isLoading && emps.length === 0 && (
              <TableRow><TableCell colSpan={7} className="text-center py-12">
                <div className="flex flex-col items-center gap-2">
                  <Users className="h-8 w-8 text-muted-foreground" />
                  <p className="text-muted-foreground">No employees found.</p>
                  <p className="text-sm text-muted-foreground">Try adjusting your search or filters.</p>
                </div>
              </TableCell></TableRow>
            )}
            {emps.map((emp) => (
              <TableRow key={emp.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-medium text-sm">
                      {emp.first_name.charAt(0)}{emp.last_name.charAt(0)}
                    </div>
                    <div>
                      <Link to={`/employees/${emp.id}`} className="font-medium hover:text-blue-600 transition-colors">
                        {emp.first_name} {emp.last_name}
                      </Link>
                      <p className="text-sm text-muted-foreground">{emp.email}</p>
                    </div>
                  </div>
                </TableCell>
                <TableCell>{emp.department ?? "-"}</TableCell>
                <TableCell>{emp.position ?? "-"}</TableCell>
                <TableCell className="hidden md:table-cell">{formatDate(emp.hire_date)}</TableCell>
                <TableCell className="hidden md:table-cell">{formatSalary(emp.salary_base)}</TableCell>
                <TableCell><Badge variant={statusVariant(emp.status)}>{emp.status.replace("_", " ")}</Badge></TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    {isManager && <Button variant="ghost" size="icon" onClick={() => handleOpenEdit(emp)}><Edit className="h-4 w-4" /></Button>}
                    {emp.status === "active" && isAdmin && <Button variant="ghost" size="icon" onClick={() => handleConfirm("deactivate", emp)}><PowerOff className="h-4 w-4" /></Button>}
                    {emp.status === "inactive" && isAdmin && <Button variant="ghost" size="icon" onClick={() => handleConfirm("restore", emp)}><Check className="h-4 w-4 text-green-600" /></Button>}
                    {isAdmin && <Button variant="ghost" size="icon" onClick={() => handleConfirm("delete", emp)}><Trash2 className="h-4 w-4 text-red-600" /></Button>}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious onClick={() => setPage((p) => Math.max(1, p - 1))} className={page <= 1 ? "pointer-events-none opacity-50" : "cursor-pointer"} />
            </PaginationItem>
            {Array.from({ length: totalPages }, (_, i) => i + 1)
              .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
              .reduce((acc: number[], p: number, idx: number, arr: number[]) => {
                if (idx > 0 && p - arr[idx - 1] > 1) acc.push(-1);
                acc.push(p);
                return acc;
              }, [])
              .map((p) =>
                p === -1 ? (
                  <PaginationItem key="el"><PaginationEllipsis /></PaginationItem>
                ) : (
                  <PaginationItem key={p}>
                    <PaginationLink onClick={() => setPage(p)} isActive={page === p} className="cursor-pointer">{p}</PaginationLink>
                  </PaginationItem>
                )
              )}
            <PaginationItem>
              <PaginationNext onClick={() => setPage((p) => Math.min(totalPages, p + 1))} className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"} />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
      {confirmAction && (
        <AlertDialog open={true} onOpenChange={(o) => !o && setConfirmAction(null)}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {confirmAction.type === "deactivate" && "Deactivate Employee?"}
                {confirmAction.type === "restore" && "Restore Employee?"}
                {confirmAction.type === "delete" && "Delete Employee?"}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {confirmAction.type === "deactivate" && (
                  <>Deactivate <strong>{confirmAction.employee.first_name} {confirmAction.employee.last_name}</strong>? They will no longer have access.</>
                )}
                {confirmAction.type === "restore" && (
                  <>Restore <strong>{confirmAction.employee.first_name} {confirmAction.employee.last_name}</strong>? They will be reactivated.</>
                )}
                {confirmAction.type === "delete" && (
                  <>Permanently delete <strong>{confirmAction.employee.first_name} {confirmAction.employee.last_name}</strong>? This cannot be undone.</>
                )}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleExecute} className={confirmAction.type === "delete" ? "bg-red-600 hover:bg-red-700" : ""}>Confirm</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}

      <EmployeeFormDialog open={modalOpen} onOpenChange={setModalOpen} employee={editing} onSubmit={(d) => editing ? handleUpdate(d as EmployeeUpdate) : handleCreate(d as EmployeeCreate)} />
    </div>
  );
}

