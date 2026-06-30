import { useEffect, useRef, useState, type FormEvent } from "react";
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
import { DataTable } from "@/components/ui/data-table";
import { EmptyState } from "@/components/ui/empty-state";
import { FormRow } from "@/components/ui/form-row";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { NormalityBadge } from "@/components/ui/normality-badge";
import { PageHeader } from "@/components/ui/page-header";
import { formatDate } from "@/lib/format";

const ALLOWED_TYPES = ["image/png", "image/jpeg", "application/pdf"];
const MAX_SIZE = 10 * 1024 * 1024;

function CreateReportModal({
  patientId,
  open,
  onClose,
}: {
  patientId: string;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const submitRef = useRef<HTMLButtonElement>(null);
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
    <Modal
      open={open}
      onClose={onClose}
      title={t("lab.form.create_report")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={() => submitRef.current?.click()} disabled={uploading}>
            {uploading ? t("common.loading") : t("lab.form.create")}
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <FormRow cols={3}>
          <div>
            <label className="block text-base font-medium text-ink mb-1">{t("lab.form.category")}</label>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full px-3 py-2 border border-border rounded-theme bg-surface text-ink text-base">
              <option value="lab">{t("lab.category.lab")}</option>
              <option value="imaging">{t("lab.category.imaging")}</option>
            </select>
          </div>
          <Input label={t("lab.form.report_date")} type="date" value={reportDate} onChange={(e) => setReportDate(e.target.value)} required />
          <Input label={t("lab.form.lab_name")} value={labName} onChange={(e) => setLabName(e.target.value)} />
        </FormRow>
        <div>
          <label className="block text-base font-medium text-ink mb-1">{t("lab.form.file")}</label>
          <input type="file" accept=".png,.jpg,.jpeg,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} className="text-base" />
          <p className="text-sm text-muted mt-1">{t("lab.upload.hint")}</p>
        </div>
        {error && <p className="text-sm text-status-warning" role="alert">{error}</p>}
        <button ref={submitRef} type="submit" className="hidden" aria-hidden="true" tabIndex={-1} />
      </form>
    </Modal>
  );
}

function AddResultModal({
  patientId,
  reportId,
  open,
  onClose,
}: {
  patientId: string;
  reportId: string;
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const submitRef = useRef<HTMLButtonElement>(null);
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
    <Modal
      open={open}
      onClose={onClose}
      title={t("lab.form.add_result")}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>{t("common.cancel")}</Button>
          <Button onClick={() => submitRef.current?.click()} disabled={mutation.isPending}>
            {mutation.isPending ? t("common.loading") : t("lab.form.add_result_btn")}
          </Button>
        </>
      }
    >
      <form onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }} className="space-y-5">
        <div>
          <Input label={t("lab.form.search_test")} value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("lab.form.search_placeholder")} />
          {catalogue && catalogue.items.length > 0 && search && (
            <div className="border border-border-light rounded-theme mt-1 max-h-40 overflow-y-auto">
              {catalogue.items.map((test) => (
                <button key={test.id} type="button" onClick={() => selectTest(test)} className="block w-full text-left px-3 py-2 text-base hover:bg-accent-50">
                  {test.display_name} {test.loinc_code && <span className="text-muted">({test.loinc_code})</span>}
                </button>
              ))}
            </div>
          )}
          {selectedTest && <p className="text-sm text-accent mt-1">{t("lab.form.selected")}: {selectedTest.display_name}</p>}
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
        <FormRow cols={3}>
          {valueType === "numeric" ? (
            <Input label={t("lab.form.value")} type="number" step="any" value={valueNumeric} onChange={(e) => setValueNumeric(e.target.value)} required />
          ) : (
            <Input label={t("lab.form.value")} value={valueText} onChange={(e) => setValueText(e.target.value)} required />
          )}
          <Input label={t("lab.form.unit")} value={unit} onChange={(e) => setUnit(e.target.value)} />
          <Input label={t("lab.form.effective_date")} type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} required />
        </FormRow>
        <Input label={t("lab.form.notes")} value={notes} onChange={(e) => setNotes(e.target.value)} />
        {error && <p className="text-sm text-status-warning" role="alert">{error}</p>}
        <button ref={submitRef} type="submit" className="hidden" aria-hidden="true" tabIndex={-1} />
      </form>
    </Modal>
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
      <PageHeader
        title={t("lab.detail.title")}
        subtitle={`${formatDate(report.report_date)} · ${report.category}${report.lab_name ? ` · ${report.lab_name}` : ""}`}
        actions={<Button onClick={() => setAddingResult(true)}>{t("lab.form.add_result_btn")}</Button>}
      />

      <AddResultModal patientId={patientId} reportId={reportId} open={addingResult} onClose={() => setAddingResult(false)} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {fileBlob && report.file_ref && (
          <Card>
            <h3 className="text-lg text-ink font-medium mb-3">{t("lab.detail.file")}</h3>
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
          <h3 className="text-lg text-ink font-medium mb-3">{t("lab.detail.results")} ({report.results.length})</h3>
          <DataTable
            columns={[
              { key: "test", header: t("summary.table_test"), render: (r) => r.display_name },
              {
                key: "value",
                header: t("summary.table_value"),
                className: "font-sans tabular-nums",
                render: (r) => (
                  <>
                    {r.value_numeric ?? r.value_text ?? ""}
                    {r.unit && <span className="text-muted ml-1">{r.unit}</span>}
                  </>
                ),
              },
              { key: "date", header: t("summary.table_date"), render: (r) => <span className="text-muted">{formatDate(r.effective_date)}</span> },
              { key: "status", header: t("summary.table_status"), render: (r) => r.normality ? <NormalityBadge status={r.normality.status} /> : null },
            ]}
            data={report.results}
            getKey={(r) => r.id}
            emptyMessage={t("summary.none_recorded")}
          />
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
        <button onClick={() => setSelectedReport(null)} className="text-sm text-accent hover:underline mb-4">
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
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="px-3 py-2 border border-border rounded-theme bg-surface text-ink text-base">
          <option value="">{t("lab.timeline.all")}</option>
          <option value="lab">{t("lab.category.lab")}</option>
          <option value="imaging">{t("lab.category.imaging")}</option>
        </select>
      </div>
      {items.length === 0 ? (
        <EmptyState title={t("lab.timeline.empty")} />
      ) : (
        <div className="space-y-2">
          {items.map((entry) => (
            <div key={entry.id} onClick={() => setSelectedReport(entry.id)} className="cursor-pointer">
              <Card className="hover:border-accent/40 transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-medium text-ink">{formatDate(entry.report_date)}</h3>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-sm text-muted capitalize">{t(`lab.category.${entry.category}`)}</span>
                      {entry.lab_name && <span className="text-sm text-muted">{entry.lab_name}</span>}
                      <span className="text-sm text-muted">{entry.result_count} {t("lab.timeline.results")}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {entry.has_out_of_range && <NormalityBadge status="above_high" />}
                    <button onClick={(e) => { e.stopPropagation(); setDeleting(entry); }} className="text-xs text-secondary hover:text-status-warning">{t("common.delete")}</button>
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
        <label className="block text-base font-medium text-ink mb-1">{t("lab.trend.select_test")}</label>
        <select value={testKey} onChange={(e) => setTestKey(e.target.value)} className="px-3 py-2 border border-border rounded-theme bg-surface text-ink text-base">
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
      {error && <span className="text-sm text-status-warning" role="alert">{error}</span>}
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

      <PageHeader
        title={t("lab.title")}
        actions={
          <div className="flex gap-3">
            <ExportButtons patientId={patientId!} />
            <Button onClick={() => setShowCreate(true)}>{t("lab.add_report")}</Button>
          </div>
        }
      />

      <CreateReportModal patientId={patientId!} open={showCreate} onClose={() => setShowCreate(false)} />

      <div className="flex gap-1 mb-6 border-b border-border-light pb-2">
        <button
          onClick={() => setTab("timeline")}
          className={`px-3 py-1.5 rounded-theme text-base ${tab === "timeline" ? "bg-accent-50 text-accent font-medium" : "text-muted hover:text-ink"}`}
        >
          {t("lab.tabs.timeline")}
        </button>
        <button
          onClick={() => setTab("trends")}
          className={`px-3 py-1.5 rounded-theme text-base ${tab === "trends" ? "bg-accent-50 text-accent font-medium" : "text-muted hover:text-ink"}`}
        >
          {t("lab.tabs.trends")}
        </button>
      </div>

      {tab === "timeline" && <TimelineView patientId={patientId!} />}
      {tab === "trends" && <LabTrendView patientId={patientId!} />}
    </div>
  );
}
