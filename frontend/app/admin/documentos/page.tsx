"use client";

import { useEffect, useRef, useState } from "react";
import { useAdminActual } from "../../../hooks/useAdminActual";
import {
  borrarDocumento,
  listarDocumentos,
  reemplazarDocumento,
  subirDocumento,
  type DocumentoOrganismo,
} from "../../../lib/admin-documentos-api";
import { listarOrganismos, type Organismo } from "../../../lib/admin-tramites-api";
import { MAX_DOCUMENTOS, cuposLibres, tituloPorDefecto, validarArchivo } from "../../../lib/documentos-ui";

export default function DocumentosPage() {
  const admin = useAdminActual();
  const esSuper = admin?.rol === "super_admin";
  const [organismos, setOrganismos] = useState<Organismo[]>([]);
  const [organismoId, setOrganismoId] = useState<number | undefined>(undefined);
  const [documentos, setDocumentos] = useState<DocumentoOrganismo[]>([]);
  const [cargando, setCargando] = useState(true);
  const [procesando, setProcesando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [titulo, setTitulo] = useState("");
  const entradaArchivo = useRef<HTMLInputElement>(null);
  const reemplazoPara = useRef<string | null>(null);
  const entradaReemplazo = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (esSuper) listarOrganismos().then(setOrganismos).catch(() => setOrganismos([]));
  }, [esSuper]);

  useEffect(() => {
    if (admin) cargar();
  }, [admin, organismoId]);

  async function cargar() {
    setCargando(true);
    try {
      setDocumentos(await listarDocumentos(esSuper ? organismoId : undefined));
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudieron cargar los documentos");
    } finally {
      setCargando(false);
    }
  }

  function elegirArchivo(f: File | null) {
    setError(null);
    if (f) {
      const problema = validarArchivo(f.name, f.size);
      if (problema) {
        setError(problema);
        setArchivo(null);
        return;
      }
      if (!titulo) setTitulo(tituloPorDefecto(f.name));
    }
    setArchivo(f);
  }

  async function ejecutar(accion: () => Promise<unknown>) {
    setProcesando(true);
    setError(null);
    try {
      await accion();
      await cargar();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ocurrió un error");
    } finally {
      setProcesando(false);
    }
  }

  async function subir() {
    if (!archivo) return;
    if (esSuper && organismoId === undefined) {
      setError("Elegí el organismo del documento.");
      return;
    }
    await ejecutar(async () => {
      await subirDocumento({ archivo, titulo: titulo.trim() || undefined, organismoId: esSuper ? organismoId : undefined });
      setArchivo(null);
      setTitulo("");
      if (entradaArchivo.current) entradaArchivo.current.value = "";
    });
  }

  async function alElegirReemplazo(f: File | null) {
    const id = reemplazoPara.current;
    if (entradaReemplazo.current) entradaReemplazo.current.value = "";
    if (!f || !id) return;
    const problema = validarArchivo(f.name, f.size);
    if (problema) {
      setError(problema);
      return;
    }
    await ejecutar(() => reemplazarDocumento(id, { archivo: f }));
  }

  async function borrar(d: DocumentoOrganismo) {
    if (!window.confirm(`¿Borrar "${d.titulo}"? El agente dejará de usarlo.`)) return;
    await ejecutar(() => borrarDocumento(d.id));
  }

  const hayOrganismo = !esSuper || organismoId !== undefined;
  const libres = cuposLibres(documentos.length);

  return (
    <div className="p-4">
      <h1 className="mb-1 text-lg font-semibold">Documentos del organismo</h1>
      <p className="mb-4 text-sm texto-secundario">
        Subí hasta {MAX_DOCUMENTOS} documentos (PDF o Word con texto, de hasta 10 MB) con información propia del
        organismo. El agente los usa para responder y cita de cuál sale cada dato.
      </p>

      {esSuper && (
        <select
          className="campo-input mb-4"
          value={organismoId ?? ""}
          onChange={(e) => setOrganismoId(e.target.value ? Number(e.target.value) : undefined)}
        >
          <option value="">Todos los organismos</option>
          {organismos.map((o) => (
            <option key={o.id} value={o.id}>
              {o.nombre}
            </option>
          ))}
        </select>
      )}

      {error && <p className="mb-3 text-sm texto-error">{error}</p>}
      {procesando && <p className="mb-3 text-sm texto-secundario">Procesando el documento, puede tardar unos segundos…</p>}

      {cargando ? (
        <p className="text-sm texto-secundario">Cargando…</p>
      ) : (
        <ul className="mb-6 space-y-2">
          {documentos.map((d) => (
            <li key={d.id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-gray-200 bg-white p-3 text-sm">
              <div className="min-w-0">
                <p className="font-semibold">{d.titulo}</p>
                <p className="texto-secundario">
                  {esSuper && `${d.organismo} · `}
                  {d.nombre_archivo} · {d.fragmentos} fragmentos · actualizado {new Date(d.actualizado_en).toLocaleDateString()}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  className="boton-secundario"
                  disabled={procesando}
                  onClick={() => {
                    reemplazoPara.current = d.id;
                    entradaReemplazo.current?.click();
                  }}
                >
                  Reemplazar
                </button>
                <button className="boton-secundario" disabled={procesando} onClick={() => borrar(d)}>
                  Borrar
                </button>
              </div>
            </li>
          ))}
          {documentos.length === 0 && <li className="text-sm texto-secundario">Todavía no hay documentos.</li>}
        </ul>
      )}

      <input
        ref={entradaReemplazo}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(e) => alElegirReemplazo(e.target.files?.[0] ?? null)}
      />

      {(esSuper ? organismoId !== undefined : true) && (
        <div className="max-w-md space-y-3">
          <h2 className="font-semibold">Subir un documento nuevo</h2>
          {libres === 0 ? (
            <p className="text-sm texto-secundario">Ya hay {MAX_DOCUMENTOS} documentos. Reemplazá o borrá uno para subir otro.</p>
          ) : (
            <>
              <p className="text-sm texto-secundario">
                Quedan {libres} {libres === 1 ? "lugar" : "lugares"}.
              </p>
              <input
                ref={entradaArchivo}
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => elegirArchivo(e.target.files?.[0] ?? null)}
              />
              <input
                className="campo-input w-full"
                placeholder="Título del documento"
                value={titulo}
                maxLength={150}
                onChange={(e) => setTitulo(e.target.value)}
              />
              <button className="boton-primario" disabled={!archivo || !hayOrganismo || procesando} onClick={subir}>
                {procesando ? "Procesando…" : "Subir documento"}
              </button>
            </>
          )}
        </div>
      )}
      {esSuper && organismoId === undefined && (
        <p className="text-sm texto-secundario">Elegí un organismo para subir un documento.</p>
      )}
    </div>
  );
}
