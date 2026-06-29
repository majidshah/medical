import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/client";
import {
  createReport,
  createResult,
  deleteReport,
  downloadFileUrl,
  exportFhir,
  exportPdf,
  getLabTrend,
  getReportDetail,
  getTimeline,
  searchCatalogue,
  uploadFile,
  type LabTest,
  type TimelineEntry,
} from "@/api/lab";
import { TrendChart } from "@/components/clinical/trend-chart";
import { PatientNav } from "@/components/layout/patient-nav";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Input } from "@/components/ui/input";
import { NormalityBadge } from "@/components/ui/normality-badge";

const ALLOWED_TYPES = ["image/png", "image/jpeg", "application/pdf"];
const MAX_SIZE = 10 * 1024 * 1024;

function CreateReportForm({
  patientId,
  onClose,
}: {
  patientId: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [category, setCategory] = useState("lab");
  const [reportDate, setReportDate] = useState("");
  const [labName, setLabName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setUploading(true);
    try {
      let fileId: string | undefined;
      if (file) {
        if (!ALLOWED_TYPES.includes(file.type)) {
          setError(t("lab.upload.type_error"));
          setUploading(false);
          return;
        }
        if (file.size > MAX_SIZE) {
          setError(t("lab.upload.size_error"));
          setUploading(false);
          return;
        }
        const stored = await uploadFile(patientId, file);
        fileId = stored.id;
      }
      await createReport(patientId, {
        category,
        report_date: reportDate,
        lab_name: labName || undefined,
        file_id: fileId,
      });
      queryClient.invalidateQueries({ queryKey: ["timeline", patientId] });
      queryClient.invalidateQueries({ queryKey: ["reports", patientId] });
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("lab.form.error"));
    } finally {
      setUploading(false);
    }
  };

  return (
    <Card className="mb-6">
      <h2 className="text-lg text-ink font-medium mb-4">{t("lab.form.create_report")}</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-base text-secondary mb-1">{t("lab.form.category")}</label>
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full px-3 py-2 border border-border rounded bg-surface text-ink text-base">
            <option value="lab">{t("lab.category.lab")}</option>
            <option value="imaging">{t("lab.category.imaging")}</option>
          </select>
        </div>
        <Input label={t("lab.form.report_date")} type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} required />
        <Input label={t("lab.form.lab_name")} value={labName} onChange={(e) => setLabName(e.target.value)} />
        <div>
          <label className="block text-base text-secondary mb-1">{t("lab.form.file")}</label>
          <input type="file" accept=".png,.jpg,.jpeg,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-base" />
          <p className="text-base text-muted mt-1">{t("lab.upload.hint")}</p>
        </div>
        {error && <p className="text-base text-status-warning" role="alert">{error}</p>}
        <div className="flex gap-3 justify-end pt-3">
          <Button type="submit" disabled={uploading}>{uploading ? t("common.loading") : t("lab.form.create")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

function AddResultForm({
  patientId,
  reportId,
  onClose,
}: {
  patientId: string;
  reportId: string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [selectedTest, setSelectedTest] = useState<LabTest | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [valueNumeric, setValueNumeric] = useState("");
  const [valueText, setValueText] = useState("");
  const [valueType, setValueType] = useState<"numeric" | "text">("numeric");
  const [unit, setUnit] = useState("");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const { data: catalogue } = useQuery({
    queryKey: ["lab-catalogue", search],
    queryFn: () => searchCatalogue({ q: search || undefined }),
    enabled: search.length > 1,
  });

  const selectTest = (test: LabTest) => {
    setSelectedTest(test);
    setDisplayName(test.display_name);
    setUnit(test.default_unit || "");
    setSearch("");
  };

  const mutation = useMutation({
    mutationFn: () =>
      createResult(patientId, reportId, {
        display_name: displayName,
        test_id: selectedTest?.id,
        value_numeric: valueType === "numeric" ? parseFloat(valueNumeric) : undefined,
        value_text: valueType === "text" ? valueText : undefined,
        unit: unit || undefined,
        effective_date: effectiveDate,
        notes: notes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report-detail", patientId, reportId] });
      queryClient.invalidateQueries({ queryKey: ["timeline", patientId] });
      onClose();
    },
    onError: (err: Error) => {
      setError(err instanceof ApiError && err.status === 422 ? err.detail : t("lab.form.error"));
    },
  });

  return (
    <Card className="mb-4">
      <h3 className="font-serif text-lg text-ink mb-3">{t("lab.form.add_result")}</h3>
      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }} className="space-y-3">
        <div>
          <Input label={t("lab.form.search_test")} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("lab.form.search_placeholder")} />
          {catalogue && catalogue.items.length > 0 && search && (
            <div className="border border-border-light rounded mt-1 max-h-40 overflow-y-auto">
              {catalogue.items.map((test) => (
                <button key={test.id} type="button" onClick={() => selectTest(test)} className="block w-full text-left px-3 py-2 text-base hover:bg-accent-50">
                  {test.display_name} {test.loinc_code && <span className="text-muted">({test.loinc_code})</span>}
                </button>
              ))}
            </div>
          )}
          {selectedTest && <p className="text-base text-accent mt-1">{t("lab.form.selected")}: {selectedTest.display_name}</p>}
        </div>
        <Input label={t("lab.form.display_name")} value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
        <div className="flex gap-4">
          <label className="flex items-center gap-2 text-base cursor-pointer">
            <input type="radio" checked={valueType === "numeric"} onChange={() => setValueType("numeric")} style={{ accentColor: "var(--accent)" }} />
            {t("lab.form.numeric")}
          </label>
          <label className="flex items-center gap-2 text-base cursor-pointer">
            <input type="radio" checked={valueType === "text"} onChange={() => setValueType("text")} style={{ accentColor: "var(--accent)" }} />
            {t("lab.form.text_value")}
          </label>
        </div>
        {valueType === "numeric" ? (
          <Input label={t("lab.form.value")} type="number" step="any" value={valueNumeric} onChange={(e) => setValueNumeric(e.target.value)} required />
        ) : (
          <Input label={t("lab.form.value")} value={valueText} onChange={(e) => setValueText(e.target.value)} required />
        )}
        <Input label={t("lab.form.unit")} value={unit} onChange={(e) => setUnit(e.target.value)} />
        <Input label={t("lab.form.effective_date")} type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} required />
        <Input label={t("lab.form.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {error && <p className="text-base text-status-warning" role="alert">{error}</p>}
        <div className="flex gap-3">
          <Button type="submit" disabled={mutation.isPending}>{mutation.isPending ? t("common.loading") : t("lab.form.add_result_btn")}</Button>
          <Button type="button" variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
        </div>
      </form>
    </Card>
  );
}

function ReportDetailView({ patientId, reportId }: { patientId: string; reportId: string }) {
  const { t } = useTranslation();
  const [fileBlob, setFileBlob] = useState<string | null>(null);
  const [addingResult, setAddingResult] = useState(false);

  const { data: report, isLoading } = useQuery({
    queryKey: ["report-detail", patientId, reportId],
    queryFn: () => getReportDetail(patientId, reportId),
  });

  useEffect(() => {
    if (report?.file_ref?.id) {
      downloadFileUrl(patientId, report.file_ref.id).then((blob) => {
        setFileBlob(URL.createObjectURL(blob));
      }).catch(() => {});
    }
  }, [report?.file_ref?.id, patientId]);

  if (isLoading || !report) return <p className="text-muted text-center py-8">{t("common.loading")}</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg text-ink font-medium">{t("lab.detail.title")}</h2>
          <p className="text-base text-muted">{report.report_date} &middot; {report.category} {report.lab_name && `· ${report.lab_name}`}</p>
        </div>
        <Button onClick={() => setAddingResult(true)}>{t("lab.form.add_result_btn")}</Button>
      </div>

      {addingResult && <AddResultForm patientId={patientId} reportId={reportId} onClose={() => setAddingResult(false)} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {fileBlob && report.file_ref && (
          <Card>
            <h3 className="font-serif text-lg text-ink mb-3">{t("lab.detail.file")}</h3>
            {report.file_ref.content_type.startsWith("image/") ? (
              <img src={fileBlob} alt={report.file_ref.original_filename} className="max-w-full rounded" />
            ) : (
              <a href={fileBlob} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline text-base">
                {report.file_ref.original_filename}
              </a>
            )}
          </Card>
        )}
        <Card>
          <h3 className="font-serif text-lg text-ink mb-3">{t("lab.detail.results")} ({report.results.length})</h3>
          {report.results.length > 0 ? (
            <table className="w-full text-base">
              <thead>
                <tr className="border-b border-border-light text-left">
                  <th className="pb-2 font-medium">{t("summary.table_test")}</th>
                  <th className="pb-2 font-medium">{t("summary.table_value")}</th>
                  <th className="pb-2 font-medium">{t("summary.table_date")}</th>
                  <th className="pb-2 font-medium">{t("summary.table_status")}</th>
                </tr>
              </thead>
              <tbody>
                {report.results.map((r) => (
                  <tr key={r.id} className="border-b border-border-light">
                    <td className="py-2">{r.display_name}</td>
                    <td className="py-2 font-sans tabular-nums">{r.value_numeric ?? r.value_text ?? ""} {r.unit && <span className="text-muted">{r.unit}</span>}</td>
                    <td className="py-2 text-muted">{r.effective_date}</td>
                    <td className="py-2">{r.normality && <NormalityBadge status={r.normality.status} />}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-muted text-base">{t("summary.none_recorded")}</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function TimelineView({ patientId }: { patientId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [category, setCategory] = useState("");
  const [selectedReport, setSelectedReport] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<TimelineEntry | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["timeline", patientId, category],
    queryFn: () => getTimeline(patientId, { category: category || undefined }),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteReport(patientId, deleting!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["timeline", patientId] });
      setDeleting(null);
      if (selectedReport === deleting?.id) setSelectedReport(null);
    },
  });

  if (selectedReport) {
    return (
      <div>
        <button onClick={() => setSelectedReport(null)} className="text-base text-accent hover:underline mb-4">
          &larr; {t("lab.timeline.back")}
        </button>
        <ReportDetailView patientId={patientId} reportId={selectedReport} />
      </div>
    );
  }

  if (isLoading) return <p className="text-muted text-center py-8">{t("common.loading")}</p>;

  const items = data?.items || [];

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="px-3 py-2 border border-border rounded bg-surface text-ink text-base">
          <option value="">{t("lab.timeline.all")}</option>
          <option value="lab">{t("lab.category.lab")}</option>
          <option value="imaging">{t("lab.category.imaging")}</option>
        </select>
      </div>
      {items.length === 0 ? (
        <Card className="text-center py-12">
          <p className="text-muted text-lg">{t("lab.timeline.empty")}</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((entry) => (
            <div key={entry.id} onClick={() => setSelectedReport(entry.id)} className="cursor-pointer">
            <Card className="hover:border-teal/40 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-medium text-ink">{entry.report_date}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-base text-muted capitalize">{t(`lab.category.${entry.category}`)}</span>
                    {entry.lab_name && <span className="text-base text-muted">{entry.lab_name}</span>}
                    <span className="text-base text-muted">{entry.result_count} {t("lab.timeline.results")}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {entry.has_out_of_range && <NormalityBadge status="above_high" />}
                  <button onClick={(e) => { e.stopPropagation(); setDeleting(entry); }} className="text-base text-status-warning hover:underline">{t("common.delete")}</button>
                </div>
              </div>
            </Card>
            </div>
          ))}
        </div>
      )}
      {deleting && (
        <ConfirmDialog
          message={t("lab.timeline.confirm_delete")}
          onConfirm={() => deleteMutation.mutate()}
          onCancel={() => setDeleting(null)}
          loading={deleteMutation.isPending}
        />
      )}
    </div>
  );
}

function LabTrendView({ patientId }: { patientId: string }) {
  const { t } = useTranslation();
  const [testKey, setTestKey] = useState("");
  const { data: catalogue } = useQuery({ queryKey: ["lab-catalogue-all"], queryFn: () => searchCatalogue({}) });
  const { data: trend } = useQuery({
    queryKey: ["lab-trend", patientId, testKey],
    queryFn: () => getLabTrend(patientId, testKey),
    enabled: !!testKey,
  });

  const tests = catalogue?.items || [];

  return (
    <div>
      <div className="mb-4">
        <label className="block text-base text-secondary mb-1">{t("lab.trend.select_test")}</label>
        <select value={testKey} onChange={(e) => setTestKey(e.target.value)} className="px-3 py-2 border border-border rounded bg-surface text-ink text-base">
          <option value="">{t("lab.trend.choose")}</option>
          {tests.map((test) => <option key={test.key} value={test.key}>{test.display_name}</option>)}
        </select>
      </div>
      {testKey && trend && (
        <TrendChart
          title={trend.test_display_name}
          points={trend.points.map((p) => ({ effective_date: p.effective_date, value: p.value, unit: p.unit }))}
          chartable={trend.chartable}
          unit={trend.range_unit}
          rangeLow={trend.range_low}
          rangeHigh={trend.range_high}
        />
      )}
    </div>
  );
}

function ExportButtons({ patientId }: { patientId: string }) {
  const { t } = useTranslation();
  const [exporting, setExporting] = useState<string | null>(null);
  const [error, setError] = useState("");

  const handleExport = async (format: "pdf" | "fhir") => {
    setExporting(format);
    setError("");
    try {
      const blob = format === "pdf" ? await exportPdf(patientId) : await exportFhir(patientId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = format === "pdf" ? "health-summary.pdf" : "health-record.fhir.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setError(t("lab.export.error"));
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <Button variant="secondary" onClick={() => handleExport("pdf")} disabled={exporting !== null}>
        {exporting === "pdf" ? t("common.loading") : t("lab.export.pdf")}
      </Button>
      <Button variant="secondary" onClick={() => handleExport("fhir")} disabled={exporting !== null}>
        {exporting === "fhir" ? t("common.loading") : t("lab.export.fhir")}
      </Button>
      {error && <span className="text-base text-status-warning" role="alert">{error}</span>}
    </div>
  );
}

export function LabReportsPage() {
  const { t } = useTranslation();
  const { patientId } = useParams<{ patientId: string }>();
  const [showCreate, setShowCreate] = useState(false);
  const [tab, setTab] = useState<"timeline" | "trends">("timeline");

  return (
    <div>
      <PatientNav patientId={patientId!} />
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg text-ink font-medium font-medium">{t("lab.title")}</h1>
        <div className="flex gap-3">
          <ExportButtons patientId={patientId!} />
          <Button onClick={() => setShowCreate(true)}>{t("lab.add_report")}</Button>
        </div>
      </div>

      {showCreate && <CreateReportForm patientId={patientId!} onClose={() => setShowCreate(false)} />}

      <div className="flex gap-1 mb-6 border-b border-border-light pb-2">
        <button
          onClick={() => setTab("timeline")}
          className={`px-3 py-1.5 rounded text-base ${tab === "timeline" ? "bg-accent-50 text-accent font-medium" : "text-muted hover:text-ink"}`}
        >
          {t("lab.tabs.timeline")}
        </button>
        <button
          onClick={() => setTab("trends")}
          className={`px-3 py-1.5 rounded text-base ${tab === "trends" ? "bg-accent-50 text-accent font-medium" : "text-muted hover:text-ink"}`}
        >
          {t("lab.tabs.trends")}
        </button>
      </div>

      {tab === "timeline" && <TimelineView patientId={patientId!} />}
      {tab === "trends" && <LabTrendView patientId={patientId!} />}
    </div>
  );
}
