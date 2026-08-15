#!/usr/bin/env python3
"""Generate payroll feature component files."""
import pathlib

ROOT = pathlib.Path(__file__).parent / "arella-hr/frontend/src"
FEAT_DIR = str(ROOT / "features/payroll")
pathlib.Path(FEAT_DIR).mkdir(parents=True, exist_ok=True)

payroll_page = r'''import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { PayrollRuns } from "./PayrollRuns";
import { DeductionRules } from "./DeductionRules";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Calendar, Building2 } from "lucide-react";

export function PayrollPage() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"runs" | "rules">("runs");

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Payroll &amp; Compensation</h1>
      </div>
      <p className="text-muted-foreground">
        Manage payroll runs, calculate compensation, and configure deduction rules.
      </p>
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "runs" | "rules")}>
        <TabsList>
          <TabsTrigger value="runs">
            <Calendar className="w-4 h-4 mr-2" />
            Payroll Runs
          </TabsTrigger>
          <TabsTrigger value="rules">
            <Building2 className="w-4 h-4 mr-2" />
            Deduction Rules
          </TabsTrigger>
        </TabsList>
        <TabsContent value="runs">
          <PayrollRuns />
        </TabsContent>
        <TabsContent value="rules">
          <DeductionRules />
        </TabsContent>
      </Tabs>
    </div>
  );
}
'''

pathlib.Path(str(ROOT / "routes" / "payroll.tsx")).write_text(
    r'export { PayrollPage } from "@/features/payroll/PayrollPage";' + "\n"
)

pathlib.Path(FEAT_DIR + "/PayrollPage.tsx").write_text(payroll_page)

print("Done: PayrollPage.tsx and routes/payroll.tsx")