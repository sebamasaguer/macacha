"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { login } from "../../../lib/admin-api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [enviando, setEnviando] = useState(false);

  async function handleSubmit(evento: FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setError(false);
    const resultado = await login(email, password);
    setEnviando(false);
    if (!resultado.ok) {
      setError(true);
      return;
    }
    router.push("/admin/chats");
  }

  return (
    <div className="flex h-screen items-center justify-center bg-white dark:bg-macacha-navy">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 p-4">
        <div className="mb-2 flex flex-col items-center gap-2">
          <img src="/branding/macacha-icon.png" alt="Macacha" className="h-12 w-12" />
          <h1 className="text-lg font-semibold text-macacha-navy dark:text-white">Ingresar</h1>
        </div>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="campo-input w-full"
          required
        />
        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="campo-input w-full"
          required
        />
        {error && <p className="text-sm texto-error">Credenciales inválidas</p>}
        <button type="submit" disabled={enviando} className="boton-primario w-full">
          {enviando ? "Ingresando…" : "Ingresar"}
        </button>
      </form>
    </div>
  );
}
