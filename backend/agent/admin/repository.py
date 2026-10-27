def crear_admin(
    conn,
    email: str,
    password_hash: str,
    rol: str = "admin_organismo",
    organismo_id: int | None = None,
    puede_crear_formularios: bool = False,
) -> None:
    # Si el admin ya existe, no se toca el permiso: volver a correr create_admin solo cambia la contraseña.
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO admins (email, password_hash, rol, organismo_id, puede_crear_formularios)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                rol = EXCLUDED.rol,
                organismo_id = EXCLUDED.organismo_id
            """,
            (email, password_hash, rol, organismo_id, puede_crear_formularios),
        )


def obtener_admin_por_email(conn, email: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, rol, organismo_id, activo FROM admins WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "email": row[1],
            "password_hash": row[2],
            "rol": row[3],
            "organismo_id": row[4],
            "activo": row[5],
        }


def obtener_admin_por_id(conn, admin_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, rol, organismo_id, activo, puede_crear_formularios FROM admins WHERE id = %s",
            (admin_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0]),
            "email": row[1],
            "rol": row[2],
            "organismo_id": row[3],
            "activo": row[4],
            "puede_crear_formularios": row[5],
        }


def listar_admins(conn) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.id, a.email, a.rol, o.nombre, a.activo, a.puede_crear_formularios
            FROM admins a
            LEFT JOIN organismos o ON o.id = a.organismo_id
            ORDER BY a.email
            """
        )
        return [
            {
                "id": str(id_),
                "email": email,
                "rol": rol,
                "organismo": organismo,
                "activo": activo,
                "puede_crear_formularios": puede,
            }
            for id_, email, rol, organismo, activo, puede in cur.fetchall()
        ]


def editar_admin(
    conn,
    admin_id: str,
    rol: str,
    organismo_id: int | None,
    activo: bool,
    password_hash: str | None = None,
    puede_crear_formularios: bool | None = None,
) -> None:
    asignaciones = ["rol = %s", "organismo_id = %s", "activo = %s"]
    parametros: list = [rol, organismo_id, activo]
    if password_hash is not None:
        asignaciones.append("password_hash = %s")
        parametros.append(password_hash)
    if puede_crear_formularios is not None:
        asignaciones.append("puede_crear_formularios = %s")
        parametros.append(puede_crear_formularios)
    parametros.append(admin_id)
    with conn.cursor() as cur:
        cur.execute(f"UPDATE admins SET {', '.join(asignaciones)} WHERE id = %s", parametros)
