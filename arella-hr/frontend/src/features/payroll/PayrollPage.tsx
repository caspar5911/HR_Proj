import { useState } from "react";
import { PayrollRuns } from "./PayrollRuns";
import { DeductionRules } from "./DeductionRules";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Calendar, Building2 } from "lucide-react";

export function PayrollPage() {
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
