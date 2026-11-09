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
    v_horario_id BIGINT;
    v_correo VARCHAR(120);
BEGIN
    IF p_semestre NOT IN (2, 3) THEN
        RAISE EXCEPTION 'Solo se permite segundo o tercer semestre.';
    END IF;

    IF p_turno NOT IN ('matutino', 'vespertino') THEN
        RAISE EXCEPTION 'El turno seleccionado no es válido.';
    END IF;

    IF p_numero_control !~ '^[0-9]{8}$' THEN
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
            'Para tercer semestre el número debe comenzar con 2532 o ser transferido desde segundo.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.reinscripcion_controles
        WHERE numero_control = p_numero_control
    ) THEN
        RAISE EXCEPTION
            'Este alumno ya está registrado en otro semestre.';
    END IF;

    SELECT horario_semestre_id
    INTO v_horario_id
    FROM public.horarios_semestre
    WHERE semestre = p_semestre
      AND turno = p_turno;

    IF v_horario_id IS NULL THEN
        RAISE EXCEPTION
            'No existe un horario registrado para este semestre y turno.';
    END IF;

    v_correo := 'l' || p_numero_control || '@acapulco.tecnm.mx';

    INSERT INTO public.reinscripcion_controles(
        numero_control, semestre_actual
    )
    VALUES (p_numero_control, p_semestre);

    IF p_semestre = 2 THEN
        INSERT INTO public.reinscripcion_segundo(
            numero_control, apellido_paterno, apellido_materno,
            nombres, turno, correo_institucional, horario_semestre_id
        )
        VALUES (
            p_numero_control, p_apellido_paterno, p_apellido_materno,
            p_nombres, p_turno, v_correo, v_horario_id
        );
    ELSE
        INSERT INTO public.reinscripcion_tercero(
            numero_control, apellido_paterno, apellido_materno,
            nombres, turno, correo_institucional, horario_semestre_id
        )
        VALUES (
            p_numero_control, p_apellido_paterno, p_apellido_materno,
            p_nombres, p_turno, v_correo, v_horario_id
        );
    END IF;

    RETURN 'Reinscripción registrada correctamente. Correo: ' || v_correo;
END;
$function$;
