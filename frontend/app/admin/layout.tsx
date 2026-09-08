"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { logout } from "../../lib/admin-api";
import { AdminAuthProvider, useAdminActual } from "../../hooks/useAdminActual";
import { HeaderInstitucional } from "../../components/HeaderInstitucional";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminLayoutInner>{children}</AdminLayoutInner>
    </AdminAuthProvider>
  );
}

function AdminLayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const admin = useAdminActual();

  if (pathname === "/admin/login") {
    return <>{children}</>;
  }

  async function handleLogout() {
    await logout();
    router.push("/admin/login");
  }

  return (
    <div className="flex h-screen flex-col bg-white text-gray-900 dark:bg-macacha-navy dark:text-gray-100">
      <HeaderInstitucional subtitulo="Panel de administración" />
      <div className="flex flex-1 overflow-hidden">
        <nav className="flex w-48 flex-col justify-between border-r border-gray-200 p-4 dark:border-white/10">
          <ul className="space-y-1 text-sm">
            <li>
              <ItemNav href="/admin/chats" pathname={pathname}>
                Chats
              </ItemNav>
            </li>
            <li>
              <ItemNav href="/admin/tramites" pathname={pathname}>
                Trámites
              </ItemNav>
            </li>
            <li>
              <ItemNav href="/admin/contacto" pathname={pathname}>
                Contacto
              </ItemNav>
            </li>
            {admin?.rol === "super_admin" && (
              <li>
                <ItemNav href="/admin/usuarios" pathname={pathname}>
                  Usuarios
                </ItemNav>
              </li>
            )}
          </ul>
          <button onClick={handleLogout} className="boton-neutro text-left">
            Cerrar sesión
          </button>
        </nav>
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

function ItemNav({
  href,
  pathname,
  children,
}: {
  href: string;
  pathname: string;
  children: React.ReactNode;
}) {
  const activo = pathname.startsWith(href);
  return (
    <Link
      href={href}
      className={
        activo
          ? "block rounded-md bg-blue-50 px-2 py-1.5 font-semibold text-macacha-blue dark:bg-macacha-blue/15 dark:text-sky-300"
          : "block rounded-md px-2 py-1.5 text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
      }
    >
      {children}
    </Link>
  );
}
