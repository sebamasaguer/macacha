"use client";

import type { TramiteDetalle } from "../lib/api";
import { CopyButton } from "./CopyButton";
import { useChecklist } from "../hooks/useChecklist";

export function TramiteInfoPanel({
  tramite,
  onPreguntar,
  preguntarDeshabilitado,
}: {
  tramite: TramiteDetalle;
  onPreguntar: (mensaje: string) => void;
  preguntarDeshabilitado: boolean;
}) {
  const { estaTildado, toggle } = useChecklist(tramite.tramite_id);

  return (
    <div className="text-gray-900 dark:text-gray-100">
      <h2 className="font-semibold">{tramite.nombre_oficial}</h2>
      <p className="text-sm texto-secundario">{tramite.organismo}</p>

      {tramite.requisitos.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Requisitos</h3>
          <ul className="mt-1 space-y-1 text-sm">
            {tramite.requisitos.map((requisito, indice) => (
              <li key={requisito} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={estaTildado("requisito", indice)}
                  onChange={() => toggle("requisito", indice)}
                  aria-label={`Marcar requisito: ${requisito}`}
                />
                <span
                  className={
                    estaTildado("requisito", indice)
                      ? "flex-1 text-gray-400 line-through dark:text-gray-500"
                      : "flex-1"
                  }
                >
                  {requisito}
                </span>
                <CopyButton texto={requisito} />
              </li>
            ))}
          </ul>
          <BotonDuda
            texto={`Tengo una duda sobre los requisitos de ${tramite.nombre_oficial}.`}
            onPreguntar={onPreguntar}
            disabled={preguntarDeshabilitado}
          />
        </div>
      )}

      {(tramite.costo || tramite.modalidad || tramite.duracion) && (
        <div className="mt-4 text-sm">
          <h3 className="font-medium">Costo, modalidad y duración</h3>
          {tramite.costo && <p>Costo: {tramite.costo}</p>}
          {tramite.modalidad && <p>Modalidad: {tramite.modalidad}</p>}
          {tramite.duracion && <p>Duración: {tramite.duracion}</p>}
          <BotonDuda
            texto={`Tengo una duda sobre el costo, la modalidad o la duración de ${tramite.nombre_oficial}.`}
            onPreguntar={onPreguntar}
            disabled={preguntarDeshabilitado}
          />
        </div>
      )}

      {tramite.pasos.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Pasos</h3>
          <ol className="mt-1 space-y-1 text-sm">
            {tramite.pasos.map((paso, indice) => (
              <li key={paso} className="flex items-start gap-2">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={estaTildado("paso", indice)}
                  onChange={() => toggle("paso", indice)}
                  aria-label={`Marcar paso: ${paso}`}
                />
                <span
                  className={
                    estaTildado("paso", indice)
                      ? "flex-1 text-gray-400 line-through dark:text-gray-500"
                      : "flex-1"
                  }
                >
                  {paso}
                </span>
                <CopyButton texto={paso} />
              </li>
            ))}
          </ol>
          <BotonDuda
            texto={`Tengo una duda sobre los pasos de ${tramite.nombre_oficial}.`}
            onPreguntar={onPreguntar}
            disabled={preguntarDeshabilitado}
          />
        </div>
      )}

      {tramite.enlaces_oficiales.length > 0 && (
        <div className="mt-4">
          <h3 className="text-sm font-medium">Enlaces oficiales</h3>
          <div className="mt-1 flex flex-col gap-2">
            {tramite.enlaces_oficiales.map((enlace) => (
              <a
                key={enlace}
                href={enlace}
                target="_blank"
                rel="noreferrer"
                className="rounded border border-macacha-blue px-3 py-1.5 text-center text-sm text-macacha-blue hover:bg-blue-50 dark:hover:bg-white/10"
              >
                {enlace}
              </a>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 text-sm">
        <h3 className="font-medium">Contacto</h3>
        {tramite.telefono_contacto && (
          <p>
            Tel: {tramite.telefono_contacto}
            <CopyButton texto={tramite.telefono_contacto} />
          </p>
        )}
        {tramite.email_contacto && (
          <p>
            Mail: {tramite.email_contacto}
            <CopyButton texto={tramite.email_contacto} />
          </p>
        )}
        {!tramite.telefono_contacto && !tramite.email_contacto && (
          <p className="texto-secundario">Sin datos de contacto.</p>
        )}
      </div>
    </div>
  );
}

function BotonDuda({
  texto,
  onPreguntar,
  disabled,
}: {
  texto: string;
  onPreguntar: (mensaje: string) => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onPreguntar(texto)}
      disabled={disabled}
      className="enlace-accion mt-2 text-xs disabled:opacity-50"
    >
      ¿Tenés dudas sobre esto?
    </button>
  );
}
