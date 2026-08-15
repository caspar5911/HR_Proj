import type { Payslip } from "@/lib/employee";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Printer } from "lucide-react";

function formatMoney(v: number): string {
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Printable payslip stub for a single payroll entry.
 *
 * The document sits in a `.print-area` div; the global print CSS (index.css)
 * hides the rest of the app so "Print / Save PDF" produces just the payslip.
 */
export function PayslipDialog({
  payslip,
  open,
  onOpenChange,
}: {
  payslip: Payslip | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open && !!payslip} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="sr-only">Payslip</DialogTitle>
        </DialogHeader>

        {payslip && (
          <div className="space-y-4">
            <div className="print-area rounded-lg border border-border bg-white">
              {/* Header */}
              <div className="flex items-start justify-between border-b border-border px-6 py-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-lg font-bold text-white">
                    A
                  </div>
                  <div>
                    <p className="text-base font-bold">Arella HR</p>
                    <p className="text-xs text-muted-foreground">People &amp; payroll platform</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold tracking-wide">PAYSLIP</p>
                  <Badge variant={payslip.run_status === "processed" ? "default" : "secondary"} className="mt-1 capitalize">
                    {payslip.run_status}
                  </Badge>
                </div>
              </div>

              {/* Period + employee */}
              <div className="grid grid-cols-2 gap-4 px-6 py-5">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Pay period
                  </p>
                  <p className="mt-1 text-sm font-medium">
                    {formatDate(payslip.period_start)} – {formatDate(payslip.period_end)}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-2">
                    Run #{payslip.run_id} · Entry #{payslip.entry_id}
                    {payslip.generated_at && (
                      <> · Generated {formatDate(payslip.generated_at)}</>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    Employee
                  </p>
                  <p className="mt-1 text-sm font-medium">{payslip.employee_name}</p>
                  <p className="text-xs text-muted-foreground">
                    {[payslip.position, payslip.department].filter(Boolean).join(" · ") || "—"}
                  </p>
                </div>
              </div>

              {/* Earnings */}
              <div className="px-6 pb-5">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                      <th className="py-2">Description</th>
                      <th className="py-2 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-dashed border-border">
                      <td className="py-2.5">Gross salary</td>
                      <td className="py-2.5 text-right font-medium tabular-nums">
                        {formatMoney(payslip.gross_salary)}
                      </td>
                    </tr>
                    {payslip.bonuses > 0 && (
                      <tr className="border-b border-dashed border-border">
                        <td className="py-2.5">Bonuses</td>
                        <td className="py-2.5 text-right font-medium tabular-nums">
                          {formatMoney(payslip.bonuses)}
                        </td>
                      </tr>
                    )}
                    <tr className="border-b border-dashed border-border">
                      <td className="py-2.5">Deductions</td>
                      <td className="py-2.5 text-right font-medium tabular-nums text-red-600">
                        −{formatMoney(payslip.deductions)}
                      </td>
                    </tr>
                    <tr>
                      <td className="py-3 text-base font-bold">Net pay</td>
                      <td className="py-3 text-right text-base font-bold tabular-nums">
                        {formatMoney(payslip.net_pay)}
                      </td>
                    </tr>
                  </tbody>
                </table>
                {payslip.notes && (
                  <p className="mt-2 rounded bg-muted px-3 py-2 text-xs text-muted-foreground">
                    Note: {payslip.notes}
                  </p>
                )}
              </div>

              <div className="border-t border-border px-6 py-3 text-center text-[11px] text-muted-foreground">
                This is a system-generated payslip stub. Figures are pre-tax estimates
                produced by Arella HR.
              </div>
            </div>

            <div className="flex justify-end gap-2 print:hidden">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
              <Button onClick={() => window.print()}>
                <Printer className="h-4 w-4 mr-2" />
                Print / Save PDF
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
