#!/usr/bin/env python3
"""Generate the employees.tsx page."""
import os

out = os.path.join(os.path.dirname(__file__), "src", "routes", "employees.tsx")

lines = [
'import { useState, useMemo, useCallback } from "react";',
'import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";',
'import { useAuth } from "@/lib/auth";',
'import {',
'  listEmployees,',
'  createEmployee,',
'  updateEmployee,',
'  deactivateEmployee,',
'  restoreEmployee,',
'  deleteEmployee,',
'  type Employee,',
'  type EmployeeCreate,',
'  type EmployeeUpdate,',
'} from "@/lib/employee";',
'import {',
'  Table,',
'  TableBody,',
'  TableCell,',
'  TableHead,',
'  TableHeader,',
'  TableRow,',
'} from "@/components/ui/table";',
'import { Badge } from "@/components/ui/badge";',
'import { Button } from "@/components/ui/button";',
'import {',
'  Dialog,',
'  DialogContent,',
'  DialogHeader,',
'  DialogTitle,',
'  DialogFooter,',
'  DialogClose,',
'} from "@/components/ui/dialog";',
'import { Input } from "@/components/ui/input";',
'import { Label } from "@/components/ui/label";',
'import { Card, CardContent } from "@/components/ui/card";',
'import {',
'  Plus, Search, Edit, Trash2, PowerOff, X, Check, AlertCircle,',
'  Building2, Briefcase, Calendar, Mail, Phone, Users,',
'} from "lucide-react";',
'',
'',
]

with open(out, "w") as f:
    f.write("\n".join(lines))

print(f"Phase 1 written: {out}")