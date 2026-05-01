import { Mic, Square, UploadCloud } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import toast from "react-hot-toast";

import { api } from "@/api/client";

type AbnormalItem = { test: string; value: number; unit?: string; status?: string; normal?: string };

const LAB_FIELDS = [
  { key: "HbA1c", placeholder: "4.0-5.7 %" },
  { key: "Fasting glucose", placeholder: "70-99 mg/dL" },
  { key: "BNP", placeholder: "0-100 pg/mL" },
  { key: "Troponin", placeholder: "0-0.04 ng/mL" },
  { key: "TSH", placeholder: "0.4-4.0 mIU/L" },
  { key: "Free T4", placeholder: "0.8-1.8 ng/dL" },
  { key: "INR", placeholder: "0.8-1.2 ratio" },
  { key: "eGFR", placeholder: ">60 mL/min/1.73m2" },
  { key: "LDL", placeholder: "<100 mg/dL" },
  { key: "Potassium", placeholder: "3.5-5.0 mEq/L" },
];

export function IngestPage() {
  const [note, setNote] = useState("");
  const [source, setSource] = useState("");
  const [entities, setEntities] = useState<string[]>([]);
  const [noteLoading, setNoteLoading] = useState(false);

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageDescription, setImageDescription] = useState("");
  const [imageLoading, setImageLoading] = useState(false);

  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [audioLoading, setAudioLoading] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  const [patientId, setPatientId] = useState("");
  const [labs, setLabs] = useState<Record<string, string>>({});
  const [customLabs, setCustomLabs] = useState<Array<{ key: string; value: string }>>([]);
  const [abnormalValues, setAbnormalValues] = useState<AbnormalItem[]>([]);
  const [tableLoading, setTableLoading] = useState(false);

  const imageDrop = useDropzone({
    accept: { "image/*": [] },
    maxFiles: 1,
    onDrop: (files) => setImageFile(files[0] ?? null),
  });

  const audioDrop = useDropzone({
    accept: { "audio/*": [], "video/*": [] },
    maxFiles: 1,
    onDrop: (files) => setAudioFile(files[0] ?? null),
  });

  const imagePreview = useMemo(() => (imageFile ? URL.createObjectURL(imageFile) : ""), [imageFile]);
  useEffect(() => {
    return () => {
      if (imagePreview) URL.revokeObjectURL(imagePreview);
    };
  }, [imagePreview]);

  const submitNote = async (e: FormEvent) => {
    e.preventDefault();
    if (!note.trim()) return;
    setNoteLoading(true);
    try {
      const res = await api.ingest.text(note, source, { section: "clinical_note" });
      toast.success(`Ingested successfully · ${res.document_id}`);
      setEntities(res.entities_found ?? []);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to ingest note");
    } finally {
      setNoteLoading(false);
    }
  };

  const submitImage = async () => {
    if (!imageFile) return;
    setImageLoading(true);
    try {
      const res = await api.ingest.image(imageFile, { section: "medical_image" });
      setImageDescription(res.description);
      toast.success(`Ingested image · ${res.document_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to ingest image");
    } finally {
      setImageLoading(false);
    }
  };

  const submitAudio = async () => {
    if (!audioFile) return;
    setAudioLoading(true);
    try {
      const res = await api.ingest.audio(audioFile, { section: "audio" });
      setTranscript(res.transcript);
      toast.success(`Ingested audio · ${res.document_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to ingest audio");
    } finally {
      setAudioLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => chunksRef.current.push(event.data);
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const file = new File([blob], `recording-${Date.now()}.webm`, { type: "audio/webm" });
        setAudioFile(file);
        stream.getTracks().forEach((track) => track.stop());
      };
      recorder.start();
      recorderRef.current = recorder;
      setRecording(true);
      setRecordingSeconds(0);
      timerRef.current = window.setInterval(() => setRecordingSeconds((seconds) => seconds + 1), 1000);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Microphone permission denied");
    }
  };

  const stopRecording = () => {
    recorderRef.current?.stop();
    setRecording(false);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const submitLabValues = async () => {
    const parsed: Record<string, number> = {};

    for (const field of LAB_FIELDS) {
      const raw = labs[field.key];
      if (raw && !Number.isNaN(Number(raw))) parsed[field.key] = Number(raw);
    }

    for (const row of customLabs) {
      if (row.key && row.value && !Number.isNaN(Number(row.value))) parsed[row.key] = Number(row.value);
    }

    if (Object.keys(parsed).length === 0) {
      toast.error("Please enter at least one lab value.");
      return;
    }

    setTableLoading(true);
    try {
      const res = await api.ingest.table(parsed, patientId);
      setAbnormalValues((res.abnormal_values as AbnormalItem[]) || []);
      toast.success(`Ingested labs · ${res.document_id}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to ingest labs");
    } finally {
      setTableLoading(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Section 1 - Clinical Note</h2>
        <form onSubmit={submitNote} className="space-y-3">
          <textarea
            rows={6}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Enter clinical note text..."
          />
          <input
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Source (optional)"
          />
          <button type="submit" disabled={noteLoading} className="rounded-md bg-primary px-4 py-2 text-sm text-white disabled:opacity-60">
            {noteLoading ? "Ingesting..." : "Ingest Clinical Note"}
          </button>
          {entities.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {entities.map((entity) => (
                <span key={entity} className="rounded-full border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs text-emerald-700">
                  {entity}
                </span>
              ))}
            </div>
          )}
        </form>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Section 2 - Medical Image</h2>
        <div {...imageDrop.getRootProps()} className="cursor-pointer rounded-md border border-dashed border-slate-300 p-4 text-center">
          <input {...imageDrop.getInputProps()} />
          <UploadCloud className="mx-auto mb-1 h-5 w-5 text-primary" />
          <p className="text-sm text-slate-600">Drop image or click to upload</p>
        </div>
        {imagePreview && <img src={imagePreview} alt="preview" className="mt-3 max-h-[200px] rounded object-contain" />}
        <button onClick={() => void submitImage()} disabled={!imageFile || imageLoading} className="mt-3 rounded-md bg-primary px-4 py-2 text-sm text-white disabled:opacity-60">
          {imageLoading ? "Processing..." : "Ingest Image"}
        </button>
        {imageDescription && <p className="mt-3 rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">{imageDescription}</p>}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Section 3 - Audio</h2>
        <div {...audioDrop.getRootProps()} className="cursor-pointer rounded-md border border-dashed border-slate-300 p-4 text-center">
          <input {...audioDrop.getInputProps()} />
          <p className="text-sm text-slate-600">Upload audio/video file</p>
        </div>
        <div className="mt-3 flex items-center gap-2">
          {!recording ? (
            <button type="button" onClick={() => void startRecording()} className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm">
              <Mic className="h-4 w-4" />
              Record
            </button>
          ) : (
            <button type="button" onClick={stopRecording} className="inline-flex items-center gap-2 rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
              <Square className="h-4 w-4" />
              Stop ({recordingSeconds}s)
            </button>
          )}
          {audioFile && <span className="text-xs text-slate-500">{audioFile.name}</span>}
        </div>
        <button onClick={() => void submitAudio()} disabled={!audioFile || audioLoading} className="mt-3 rounded-md bg-primary px-4 py-2 text-sm text-white disabled:opacity-60">
          {audioLoading ? "Processing..." : "Ingest Audio"}
        </button>
        {transcript && <pre className="mt-3 whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">{transcript}</pre>}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-700">Section 4 - Lab Values</h2>
        <div className="mb-3">
          <input
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            placeholder="Patient ID (optional)"
          />
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {LAB_FIELDS.map((field) => (
            <label key={field.key} className="text-xs text-slate-600">
              {field.key}
              <input
                value={labs[field.key] ?? ""}
                onChange={(e) => setLabs((prev) => ({ ...prev, [field.key]: e.target.value }))}
                className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2 text-sm"
                placeholder={field.placeholder}
              />
            </label>
          ))}
          {customLabs.map((row, index) => (
            <div key={`${row.key}-${index}`} className="rounded-md border border-slate-200 p-2">
              <input
                value={row.key}
                onChange={(e) => {
                  const next = [...customLabs];
                  next[index].key = e.target.value;
                  setCustomLabs(next);
                }}
                className="mb-1 w-full rounded border border-slate-300 px-2 py-1 text-xs"
                placeholder="Custom test"
              />
              <input
                value={row.value}
                onChange={(e) => {
                  const next = [...customLabs];
                  next[index].value = e.target.value;
                  setCustomLabs(next);
                }}
                className="w-full rounded border border-slate-300 px-2 py-1 text-xs"
                placeholder="Value"
              />
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={() => setCustomLabs((prev) => [...prev, { key: "", value: "" }])} className="rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-700">
            Add more
          </button>
          <button onClick={() => void submitLabValues()} disabled={tableLoading} className="rounded-md bg-primary px-4 py-2 text-sm text-white disabled:opacity-60">
            {tableLoading ? "Processing..." : "Ingest Lab Values"}
          </button>
        </div>
        {abnormalValues.length > 0 && (
          <div className="mt-3 space-y-1">
            {abnormalValues.map((item, index) => (
              <div
                key={`${item.test}-${index}`}
                className={`rounded-md border px-3 py-2 text-sm ${
                  item.status === "HIGH" ? "border-red-300 bg-red-50 text-red-700" : "border-amber-300 bg-amber-50 text-amber-700"
                }`}
              >
                {item.test}: {item.value} {item.unit ?? ""} ({item.status ?? "ABNORMAL"}) normal {item.normal ?? "range"}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

