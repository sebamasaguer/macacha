from agent.orchestrator import SYSTEM_PROMPT


def _normalizado():
    return " ".join(SYSTEM_PROMPT.split())


def test_ordena_buscar_primero_aunque_el_mensaje_sea_emocional_o_vago():
    prompt = _normalizado()

    assert "llamá siempre primero a buscar_tramite" in prompt
    assert "aunque el mensaje sea emocional o vago" in prompt


def test_solo_permite_responder_sin_buscar_ante_saludos_o_temas_ajenos():
    prompt = _normalizado()

    assert "un saludo" in prompt
    assert "no tiene relación con ningún trámite" in prompt


def test_prohibe_consejos_generales_fuera_de_las_herramientas():
    prompt = _normalizado()

    assert "Nunca des consejos generales" in prompt
    assert "tu única fuente" in prompt


def test_exige_voseo_rioplatense():
    prompt = _normalizado()

    assert "voseo rioplatense" in prompt
    assert "nunca uses" in prompt.lower()


def test_pide_no_mezclar_datos_de_tramites_parecidos():
    prompt = _normalizado()

    assert "no mezcles" in prompt


def test_el_contacto_con_una_persona_va_despues_de_buscar():
    prompt = _normalizado()

    assert "después de haber buscado" in prompt


def test_buscar_primero_tambien_cuando_la_persona_atraviesa_una_situacion_dificil():
    prompt = _normalizado()

    assert "situación difícil" in prompt
    assert "primero buscá y después" in prompt


def test_no_ofrece_contacto_sin_haber_buscado_antes():
    prompt = _normalizado()

    assert "No uses ofrecer_contacto_humano sin haber llamado antes a buscar_tramite" in prompt


def test_aclara_la_forma_correcta_de_necesitar_en_voseo():
    prompt = _normalizado()

    assert "necesitás, no necesitas" in prompt


def test_no_presenta_como_respuesta_un_trámite_que_no_es_lo_pedido():
    prompt = _normalizado()

    assert "no es lo que la persona pidió" in prompt
    assert "no se lo presentes como la respuesta" in prompt


def test_no_promete_el_formulario_sin_llamar_a_ofrecer_contacto_humano():
    prompt = _normalizado()

    assert "Nunca le digas que va a aparecer un formulario de contacto" in prompt


def test_ordena_buscar_formularios_cuando_la_persona_quiere_anotarse():
    prompt = _normalizado()

    assert "llamá a buscar_formularios" in prompt
    assert "anotarse, inscribirse o completar un formulario" in prompt


def test_exige_avisar_la_finalidad_antes_de_pedir_datos():
    prompt = _normalizado()

    assert "qué organismo los recibe y para qué" in prompt
    assert "dejá que decida si sigue" in prompt


def test_exige_resumir_y_confirmar_antes_de_guardar_y_permite_cancelar():
    prompt = _normalizado()

    assert "resumilos y preguntale si son correctos" in prompt
    assert "guardar_respuesta_formulario con confirmado en verdadero" in prompt
    assert "no guardes nada" in prompt


def test_prohibe_decir_que_se_guardo_sin_que_la_herramienta_lo_confirme():
    prompt = _normalizado()

    assert "Nunca digas que quedó registrado" in prompt
    assert "nunca inventes datos" in prompt
