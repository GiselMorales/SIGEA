
BEGIN;
-- 1. USUARIOS
CREATE TABLE usuarios (
    usuario_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre_usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasena_hash TEXT NOT NULL,
    rol VARCHAR(20) NOT NULL
        CHECK (rol IN ('administrativo', 'docente')),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. CARRERAS
CREATE TABLE carreras (
    carrera_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    clave VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    descripcion TEXT,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. PERIODOS ESCOLARES
CREATE TABLE periodos_escolares (
    periodo_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(20) NOT NULL UNIQUE,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (fecha_fin > fecha_inicio)
);

-- 4. ADMINISTRATIVOS
CREATE TABLE administrativos (
    rfc dom_rfc PRIMARY KEY
        CHECK (CHAR_LENGTH(rfc) = 13),

    usuario_id BIGINT NOT NULL UNIQUE
        REFERENCES usuarios(usuario_id),

    nombres dom_nombre NOT NULL,
    apellido_paterno dom_apellido NOT NULL,
    apellido_materno dom_apellido,

    curp dom_curp NOT NULL UNIQUE,
    sexo dom_sexo NOT NULL,
    fecha_nacimiento DATE NOT NULL,

    domicilio TEXT NOT NULL,
    codigo_postal dom_codigo_postal NOT NULL,
    telefono dom_telefono NOT NULL,
    correo dom_correo NOT NULL UNIQUE,

    tipo_sanguineo dom_tipo_sanguineo,

    contacto_emergencia_nombre dom_nombre NOT NULL,
    contacto_emergencia_parentesco VARCHAR(40) NOT NULL,
    contacto_emergencia_telefono dom_telefono NOT NULL,

    grado_academico dom_grado_academico NOT NULL,
    puesto VARCHAR(100) NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. DOCENTES
CREATE TABLE docentes (
    rfc dom_rfc PRIMARY KEY
        CHECK (CHAR_LENGTH(rfc) = 13),

    usuario_id BIGINT NOT NULL UNIQUE
        REFERENCES usuarios(usuario_id),

    nombres dom_nombre NOT NULL,
    apellido_paterno dom_apellido NOT NULL,
    apellido_materno dom_apellido,

    curp dom_curp NOT NULL UNIQUE,
    sexo dom_sexo NOT NULL,
    fecha_nacimiento DATE NOT NULL,

    domicilio TEXT NOT NULL,
    codigo_postal dom_codigo_postal NOT NULL,
    telefono dom_telefono NOT NULL,
    correo dom_correo NOT NULL UNIQUE,

    tipo_sanguineo dom_tipo_sanguineo,

    contacto_emergencia_nombre dom_nombre NOT NULL,
    contacto_emergencia_parentesco VARCHAR(40) NOT NULL,
    contacto_emergencia_telefono dom_telefono NOT NULL,

    grado_academico dom_grado_academico NOT NULL,
    cedula_profesional VARCHAR(20) UNIQUE,
    especialidad VARCHAR(120) NOT NULL,
    fecha_contratacion DATE NOT NULL,

    activo BOOLEAN NOT NULL DEFAULT TRUE,
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (
        cedula_profesional IS NULL
        OR cedula_profesional ~ '^[0-9]{7,12}$'
    )
);

-- 6. ALUMNOS
CREATE TABLE alumnos (
    alumno_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    numero_control VARCHAR(20) NOT NULL UNIQUE,
    numero_ficha VARCHAR(20) UNIQUE,

    nombres dom_nombre NOT NULL,
    apellido_paterno dom_apellido NOT NULL,
    apellido_materno dom_apellido,

    curp dom_curp NOT NULL UNIQUE,
    fecha_nacimiento DATE NOT NULL,
    sexo dom_sexo NOT NULL,

    domicilio TEXT NOT NULL,
    codigo_postal dom_codigo_postal NOT NULL,
    telefono dom_telefono NOT NULL,

    correo_personal dom_correo UNIQUE,
    correo_institucional dom_correo NOT NULL UNIQUE,

    carrera_id BIGINT NOT NULL
        REFERENCES carreras(carrera_id),

    semestre_actual SMALLINT NOT NULL DEFAULT 1
        CHECK (semestre_actual BETWEEN 1 AND 12),

    promedio_admision NUMERIC(5,2)
        CHECK (promedio_admision BETWEEN 0 AND 100),

    puntaje_examen_admision NUMERIC(6,2)
        CHECK (puntaje_examen_admision >= 0),

    escuela_procedencia VARCHAR(150),

    promedio_previo NUMERIC(5,2)
        CHECK (promedio_previo BETWEEN 0 AND 100),

    tipo_sanguineo dom_tipo_sanguineo,

    contacto_emergencia_nombre dom_nombre NOT NULL,
    contacto_emergencia_parentesco VARCHAR(40) NOT NULL,
    contacto_emergencia_telefono dom_telefono NOT NULL,

    turno VARCHAR(15) NOT NULL
        CHECK (turno IN ('matutino', 'vespertino')),

    documentos_completos BOOLEAN NOT NULL DEFAULT FALSE,

    estado VARCHAR(20) NOT NULL DEFAULT 'aspirante'
        CHECK (
            estado IN (
                'aspirante',
                'activo',
                'baja',
                'egresado'
            )
        ),

    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 7. INSCRIPCIONES INICIALES
CREATE TABLE inscripciones (
    inscripcion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alumno_id BIGINT NOT NULL UNIQUE
        REFERENCES alumnos(alumno_id),

    periodo_ingreso_id BIGINT NOT NULL
        REFERENCES periodos_escolares(periodo_id),

    fecha_inscripcion DATE NOT NULL DEFAULT CURRENT_DATE,
    ficha_entregada BOOLEAN NOT NULL DEFAULT FALSE,
    examen_admision_presentado BOOLEAN NOT NULL DEFAULT FALSE,

    observaciones TEXT,

    estado VARCHAR(20) NOT NULL DEFAULT 'registrada'
        CHECK (
            estado IN ('registrada', 'aceptada', 'cancelada')
        ),

    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. REINSCRIPCIONES
CREATE TABLE reinscripciones (
    reinscripcion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alumno_id BIGINT NOT NULL
        REFERENCES alumnos(alumno_id),

    periodo_id BIGINT NOT NULL
        REFERENCES periodos_escolares(periodo_id),

    semestre SMALLINT NOT NULL
        CHECK (semestre BETWEEN 1 AND 12),

    fecha_reinscripcion DATE NOT NULL DEFAULT CURRENT_DATE,

    estado VARCHAR(20) NOT NULL DEFAULT 'registrada'
        CHECK (
            estado IN ('registrada', 'confirmada', 'cancelada')
        ),

    observaciones TEXT,

    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (alumno_id, periodo_id)
);

-- 9. MATERIAS
CREATE TABLE materias (
    materia_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    clave VARCHAR(20) NOT NULL UNIQUE,
    nombre VARCHAR(120) NOT NULL,

    carrera_id BIGINT NOT NULL
        REFERENCES carreras(carrera_id),

    semestre SMALLINT NOT NULL
        CHECK (semestre BETWEEN 1 AND 12),

    creditos SMALLINT NOT NULL
        CHECK (creditos > 0),

    horas_teoricas SMALLINT NOT NULL DEFAULT 0
        CHECK (horas_teoricas >= 0),

    horas_practicas SMALLINT NOT NULL DEFAULT 0
        CHECK (horas_practicas >= 0),

    activa BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (carrera_id, nombre)
);

-- 10. GRUPOS
CREATE TABLE grupos (
    grupo_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    clave_grupo VARCHAR(20) NOT NULL,

    materia_id BIGINT NOT NULL
        REFERENCES materias(materia_id),

    periodo_id BIGINT NOT NULL
        REFERENCES periodos_escolares(periodo_id),

    docente_rfc dom_rfc NOT NULL
        REFERENCES docentes(rfc),

    cupo SMALLINT NOT NULL DEFAULT 30
        CHECK (cupo > 0),

    aula VARCHAR(30),

    activo BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (clave_grupo, materia_id, periodo_id)
);

-- 11. HORARIOS
CREATE TABLE horarios (
    horario_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    grupo_id BIGINT NOT NULL
        REFERENCES grupos(grupo_id),

    dia_semana VARCHAR(10) NOT NULL
        CHECK (
            dia_semana IN (
                'lunes',
                'martes',
                'miercoles',
                'jueves',
                'viernes',
                'sabado'
            )
        ),

    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,

    aula VARCHAR(30),

    CHECK (hora_fin > hora_inicio)
);

-- 12. ALUMNOS INSCRITOS EN GRUPOS
CREATE TABLE alumno_grupo (
    alumno_grupo_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alumno_id BIGINT NOT NULL
        REFERENCES alumnos(alumno_id),

    grupo_id BIGINT NOT NULL
        REFERENCES grupos(grupo_id),

    fecha_asignacion TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    estado VARCHAR(20) NOT NULL DEFAULT 'inscrito'
        CHECK (
            estado IN ('inscrito', 'baja', 'finalizado')
        ),

    UNIQUE (alumno_id, grupo_id)
);

-- 13. CALIFICACIONES
CREATE TABLE calificaciones (
    calificacion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alumno_grupo_id BIGINT NOT NULL
        REFERENCES alumno_grupo(alumno_grupo_id),

    unidad SMALLINT NOT NULL
        CHECK (unidad BETWEEN 1 AND 3),

    calificacion NUMERIC(5,2) NOT NULL
        CHECK (calificacion BETWEEN 0 AND 100),

    observaciones TEXT,

    fecha_captura TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (alumno_grupo_id, unidad)
);

-- 14. SOLICITUDES DE CONSTANCIA
CREATE TABLE solicitudes_constancia (
    solicitud_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alumno_id BIGINT NOT NULL
        REFERENCES alumnos(alumno_id),

    tipo_constancia VARCHAR(60) NOT NULL,

    fecha_solicitud TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (
            estado IN (
                'pendiente',
                'en_proceso',
                'aprobada',
                'rechazada',
                'entregada'
            )
        ),

    observaciones TEXT,

    fecha_resolucion TIMESTAMPTZ
);

-- 15. DOCUMENTOS DE ALUMNOS
CREATE TABLE documentos_alumno (
    documento_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alumno_id BIGINT NOT NULL
        REFERENCES alumnos(alumno_id),

    tipo_documento VARCHAR(60) NOT NULL,
    nombre_archivo VARCHAR(255) NOT NULL,
    ruta_archivo TEXT NOT NULL,

    entregado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_entrega DATE,

    observaciones TEXT,

    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 16. BITACORA DE AUDITORIA
CREATE TABLE bitacora_auditoria (
    auditoria_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    fecha_evento TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    tabla_afectada VARCHAR(100) NOT NULL,

    operacion VARCHAR(10) NOT NULL
        CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE')),

    usuario_bd TEXT NOT NULL DEFAULT CURRENT_USER,

    usuario_id BIGINT
        REFERENCES usuarios(usuario_id)
        ON DELETE SET NULL,

    clave_registro TEXT,

    valores_anteriores JSONB,
    valores_nuevos JSONB
);


ALTER TABLE usuarios
RENAME COLUMN contrasena_hash TO contrasena;

COMMIT;
