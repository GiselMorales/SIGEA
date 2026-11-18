CREATE OR REPLACE FUNCTION public.registrar_reinscripcion(
    p_numero_control character varying,
    p_apellido_paterno character varying,
    p_apellido_materno character varying,
    p_nombres character varying,
    p_semestre smallint,
    p_turno character varying
)
RETURNS text
LANGUAGE plpgsql
AS $function$
DECLARE
    v_periodo_id BIGINT;
    v_periodos BIGINT;
    v_horario_id BIGINT;
    v_horarios BIGINT;
    v_numero_control VARCHAR(20);
    v_nombres VARCHAR(120);
    v_apellido_paterno VARCHAR(120);
    v_apellido_materno VARCHAR(120);
    v_reinscripcion_id BIGINT;
    v_semestre_actual SMALLINT;
    v_estado VARCHAR(20);
    v_tiene_reinscripcion BOOLEAN;
    v_turno VARCHAR(15);
BEGIN
    IF p_semestre IS NULL OR p_semestre NOT IN (2, 3) THEN
        RAISE EXCEPTION 'Solo se permite segundo o tercer semestre.';
    END IF;

    v_turno := LOWER(BTRIM(COALESCE(p_turno, '')));
    IF v_turno NOT IN ('matutino', 'vespertino') THEN
        RAISE EXCEPTION 'El turno seleccionado no es válido.';
    END IF;

    IF p_numero_control IS NULL
       OR p_numero_control !~ '^[0-9]{8}$' THEN
        RAISE EXCEPTION 'El número de control debe contener 8 dígitos.';
    END IF;

    IF p_semestre = 2 AND p_numero_control NOT LIKE '2632%' THEN
        RAISE EXCEPTION
            'Para segundo semestre el número debe comenzar con 2632.';
    END IF;

    IF p_semestre = 3
       AND p_numero_control NOT LIKE '2532%'
       AND p_numero_control NOT LIKE '2632%' THEN
        RAISE EXCEPTION
            'Para tercer semestre el número debe comenzar con 2532 o 2632.';
    END IF;

    SELECT COUNT(*), MIN(periodo_id)
    INTO v_periodos, v_periodo_id
    FROM public.periodos_escolares
    WHERE CURRENT_DATE BETWEEN fecha_inicio AND fecha_fin;

    IF v_periodos = 0 THEN
        RAISE EXCEPTION 'No hay un periodo escolar vigente para hoy.';
    END IF;
    IF v_periodos > 1 THEN
        RAISE EXCEPTION 'Hay más de un periodo escolar vigente para hoy; corrige las fechas.';
    END IF;

    SELECT numero_control, nombres, apellido_paterno, apellido_materno
    INTO v_numero_control, v_nombres, v_apellido_paterno, v_apellido_materno
    FROM public.alumnos
    WHERE numero_control = p_numero_control
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'No existe un alumno con el número de control indicado.';
    END IF;

    IF LOWER(BTRIM(COALESCE(p_nombres, '')))
           IS DISTINCT FROM LOWER(BTRIM(COALESCE(v_nombres, '')))
       OR LOWER(BTRIM(COALESCE(p_apellido_paterno, '')))
           IS DISTINCT FROM LOWER(BTRIM(COALESCE(v_apellido_paterno, '')))
       OR LOWER(BTRIM(COALESCE(p_apellido_materno, '')))
           IS DISTINCT FROM LOWER(BTRIM(COALESCE(v_apellido_materno, ''))) THEN
        RAISE EXCEPTION
            'El nombre capturado no coincide con el alumno registrado.';
    END IF;

    SELECT reinscripcion_id, semestre, estado
    INTO v_reinscripcion_id, v_semestre_actual, v_estado
    FROM public.reinscripciones
    WHERE numero_control = p_numero_control
      AND periodo_id = v_periodo_id
    FOR UPDATE;
    v_tiene_reinscripcion := FOUND;

    SELECT COUNT(*), MIN(horario_semestre_id)
    INTO v_horarios, v_horario_id
    FROM public.horarios_semestre
    WHERE semestre = p_semestre AND LOWER(turno) = v_turno;

    IF v_horarios = 0 THEN
        RAISE EXCEPTION
            'No existe un horario registrado para este semestre y turno.';
    END IF;
    IF v_horarios > 1 THEN
        RAISE EXCEPTION 'Hay más de un horario para este semestre y turno; corrige la configuración.';
    END IF;

    IF v_tiene_reinscripcion THEN
        IF v_semestre_actual = 2
           AND p_semestre = 3
           AND p_numero_control LIKE '2632%'
           AND COALESCE(v_estado, '') <> 'cancelada' THEN
            UPDATE public.reinscripciones
            SET semestre = 3,
                horario_semestre_id = v_horario_id
            WHERE reinscripcion_id = v_reinscripcion_id;

            RETURN 'Alumno promovido a tercer semestre correctamente.';
        END IF;

        RAISE EXCEPTION
            'El alumno ya tiene una reinscripción para este periodo.';
    END IF;

    INSERT INTO public.reinscripciones (
        numero_control,
        periodo_id,
        semestre,
        horario_semestre_id
    )
    VALUES (
        v_numero_control,
        v_periodo_id,
        p_semestre,
        v_horario_id
    );

    RETURN 'Reinscripción registrada correctamente.';
END;
$function$;
