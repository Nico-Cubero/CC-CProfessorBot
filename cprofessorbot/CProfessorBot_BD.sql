/*******************************************************************************
 * Código para la implementación del esquema de la base de datos local usada
 * 	por el sistema cprofessorbot para el almacenamiento de toda la
 * 	información pertinente
 * Creado por: Nicolás Cubero Torres
 ******************************************************************************/

-- Eliminación de Relaciones que pudieran existir
DROP TABLE IF EXISTS Comunicado_Foro;
DROP TABLE IF EXISTS Dato_Concepto;
DROP TABLE IF EXISTS Dato_Comunicado;
DROP TABLE IF EXISTS Dato_Mensaje;
DROP TABLE IF EXISTS Foro_Usuario;
DROP TABLE IF EXISTS Comunicado;
DROP TABLE IF EXISTS ConceptoPregunta;
DROP TABLE IF EXISTS Concepto;
DROP TABLE IF EXISTS DatoLocalizacion;
DROP TABLE IF EXISTS DatoContacto;
DROP TABLE IF EXISTS DatoArchivoSticker;
DROP TABLE IF EXISTS DatoArchivo;
DROP TABLE IF EXISTS DatoTexto;
DROP TABLE IF EXISTS Dato;
DROP TABLE IF EXISTS PreguntaEfectuadaChatGrupal;
DROP TABLE IF EXISTS PreguntaEfectuadaChatPrivado;
DROP TABLE IF EXISTS MensajeRecibidoPrivado;
DROP TABLE IF EXISTS MensajeRecibidoPublico;
DROP TABLE IF EXISTS MensajeEnviadoPublico;
DROP TABLE IF EXISTS MensajeEnviadoPrivado;
DROP TABLE IF EXISTS Mensaje_Mensaje_Editado;
DROP TABLE IF EXISTS Mensaje_Mensaje_Respuesta;
DROP TABLE IF EXISTS Mensaje;
DROP TABLE IF EXISTS EventoChatGrupal;
DROP TABLE IF EXISTS Evento;
DROP TABLE IF EXISTS Foro;
DROP TABLE IF EXISTS Usuario;

/**************************************************************************
* 													TIPOS DE DATOS DEFINIDOS 											*
***************************************************************************
* En la siguiente declaración se definen los tipos de datos que han sido
*	definidos para su uso en esta base de datos para este dominio y que serán
*	convertidos a tipos admitidos por SQLite tal y como se explica a continuación
*
* - DATE: Mapeado definido por defecto en SQLite
*					Se almacena como INTEGER y se representa como un objeto DateTime
*					INTEGER (fecha y hora en EPOCH) ------------> DateTime
*
* - BOOLEAN: Se almacena como INTEGER y se representa como Bool,
*							existiendo la siguiente correspondencia:
*							Bool --------- INTEGER
*							true							1
*							false							0
*
* - TIPO_USUARIO: Se almacena como INTEGER y se representa como String,
*									existiendo la siguiente correspondencia:
*									STRING ------------ INTEGER
*									'alumno'							0
*									'docente'							1
*
* - TIPO_FORO: Se almacena como INTEGER y se representa como String,
*									existiendo la siguiente correspondencia:
*									STRING ------------ INTEGER
*									'grupo'							0
*									'supergrupo'				1
*
* - TIPO_EVENTO_CHAT_GRUPAL: Se almacena como INTEGER y se representa como
*									String, existiendo la siguiente correspondencia:
*									STRING ------------ INTEGER
*									'entrada'							0
*									'salida'							1
*									'registro'						2
*									'ban'									3
*									'readmision'					4
*									'expulsion'						5
*
* - TIPO_DATOARCHIVO: Se almacena como INTEGER y se representa como
*									String, existiendo la siguiente correspondencia:
*									STRING ------------ INTEGER
*									'imagen'							0
*									'video'								1
*									'audio'								2
*									'nota_voz'						3
*									'nota_video'					4
*									'animacion'						5
*									'documento'						6
*									'sticker'							7
*
* - TIPO_STICKER: Se almacena como INTEGER y se representa como
*									String, existiendo la siguiente correspondencia:
*									STRING ------------ INTEGER
*									'normal'							0
*									'animado'							1
******************************************************************************/

-- Relación: Usuario
CREATE TABLE Usuario (
	id INTEGER PRIMARY_KEY NOT NULL UNIQUE,
	nombre TEXT NOT NULL,
	apellidos TEXT,
	username TEXT,
	id_chat INTEGER NOT NULL UNIQUE,
	fecha_registro DATE NOT NULL, --Fecha y hora en EPOCH
	tipo TIPO_USUARIO NOT NULL CHECK (tipo IN (0,1)), -- 0: Usuario Alumno 1: Usuario Docente
	valido BOOLEAN NOT NULL DEFAULT 1
);

-- Relación: Foro
CREATE TABLE Foro (
	id_chat INTEGER PRIMARY KEY NOT NULL UNIQUE,
	nombre TEXT,
	tipo TIPO_FORO NOT NULL, -- 0: Grupo, 1: Supergrupo
	valido BOOLEAN NOT NULL CHECK (valido IN (0, 1)),
	fecha_registro DATE NOT NULL DEFAULT (DATE('now','unixepoch'))
);

-- Relación: Evento
CREATE TABLE Evento (
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
	fecha DATE DEFAULT (DATE('now','unixepoch'))
);

-- Relación: EventoChatGrupal
-- Descripción: Representa un subtipo del tipo de entidad Evento que representa
--							un evento sucedido en un chat de grupo
CREATE TABLE EventoChatGrupal (
	id INTEGER PRIMARY KEY NOT NULL,
	tipo TIPO_EVENTO_CHAT_GRUPAL NOT NULL, -- CHECK (tipo IN ('entrada', 'salida', 'registro', 'ban', 'readmision', 'expulsion')),
	id_usuario INTEGER NOT NULL,
	id_chat_foro INTEGER NOT NULL,

	FOREIGN KEY(id) REFERENCES Evento(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_usuario) REFERENCES Usuario(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_chat_foro) REFERENCES Foro(id_chat) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Mensaje
-- Descripción: Representa un subtipo del tipo de entidad Evento que representa un
--							Mensaje que es enviado o recibido en un grupo o en un chat
--							privado
CREATE TABLE Mensaje (
	id INTEGER PRIMARY KEY NOT NULL,
	id_mensaje_chat INTEGER NOT NULL,
	existente BOOLEAN CHECK (existente IN (0,1)) DEFAULT 1,

	-- Quizás convendría extender el campo existente para distinguir correctamente
	--	entre mensaje existente, mensaje válido o mensaje borrado, lo cual ahorra
	--	la necesidad de consultar el las tablas con la relación reflexiva, lo
	--	mismo sucede con añadir un campo respuesta.
	--	Por ahora no sería muy necesario hacer esto puesto que las operaciones
	--	en las que se necesita consultar esta información son aquellas en las que
	--	es necesario recopilar información, por lo que ya en sí es costosa.

	FOREIGN KEY(id) REFERENCES Evento(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Mensaje_Mensaje_Respuesta
-- Descripción: Representa un tipo de interrelación entre un dos entidades del
--							tipo de entidad Mensaje, de forma que un Mensaje responde
--							a otro mensaje
CREATE TABLE Mensaje_Mensaje_Respuesta (
	id_mensaje_respuesta INTEGER PRIMARY KEY NOT NULL,
	id_mensaje_original INTEGER NOT NULL,

	FOREIGN KEY(id_mensaje_respuesta) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_mensaje_original) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Mensaje_Mensaje_Editado
-- Descripción: Representa un tipo de interrelación entre un dos entidades del
--							tipo de entidad Mensaje, de forma que un Mensaje resulta de
--							editar otro mensaje
CREATE TABLE Mensaje_Mensaje_Editado (
	id_mensaje_nuevo INTEGER PRIMARY KEY NOT NULL,
	id_mensaje_original INTEGER NOT NULL,

	FOREIGN KEY(id_mensaje_nuevo) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_mensaje_original) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: MensajeEnviadoPrivado
-- Descripción: Representa un subtipo de un Mensaje que es enviado por el
--				sistema en un chat privado
CREATE TABLE MensajeEnviadoPrivado (
	id INTEGER PRIMARY KEY NOT NULL,
	--fecha INTEGER NOT NULL, -- Fecha en epoch
	id_usuario_destinatario INTEGER NOT NULL,

	FOREIGN KEY(id) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_usuario_destinatario) REFERENCES Usuario(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: MensajeEnviadoPublico
-- Descripción: Representa un subtipo de un Mensaje que es enviado por el
--				sistema en un chat público
CREATE TABLE MensajeEnviadoPublico (
	id INTEGER PRIMARY KEY NOT NULL,
	--fecha INTEGER NOT NULL, -- Fecha en epoch
	id_chat_foro_destino INTEGER NOT NULL,

	FOREIGN KEY(id) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_chat_foro_destino) REFERENCES Foro(id_chat) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: MensajeRecibidoPrivado
-- Descripción: Representa un subtipo de un Mensaje que es recibido por el
--				sistema en un chat público
CREATE TABLE MensajeRecibidoPrivado (
	id INTEGER PRIMARY KEY NOT NULL,
	-- fecha INTEGER NOT NULL, -- Fecha en epoch
	id_usuario_emisor INTEGER NOT NULL,

	FOREIGN KEY(id) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_usuario_emisor) REFERENCES Usuario(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: MensajeRecibidoPublico
-- Descripción: Representa un subtipo de un Mensaje que es recibido por el
--				sistema en un chat público
CREATE TABLE MensajeRecibidoPublico (
	id INTEGER PRIMARY KEY NOT NULL,
	-- fecha INTEGER NOT NULL, -- Fecha en epoch
	academico BOOLEAN CHECK (academico IN (0, 1)),
	id_usuario_emisor INTEGER NOT NULL,
	id_chat_foro INTEGER NOT NULL,
	--CHECK(NOT EXISTS(SELECT id FROM Usuario WHERE Usuario.id=id_usuario_emisor AND Usuario.tipo=1) OR academico IS NULL),
	-- EXISTS(SELECT id FROM Usuario WHERE Usuario.id=id_usuario_emisor AND Usuario.tipo=1) => academico IS NULL
	-- Para los usuarios docentes, el campo academico no debe de contener ningún valor

	FOREIGN KEY(id) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_chat_foro) REFERENCES Foro(id_chat) ON DELETE RESTRICT ON UPDATE RESTRICT
);

--	Relación: PreguntaEfectuadaChatPrivado
--	Representa: Representa el atributo compuesto "pregunta_efectuada" del
--							subtipo de entidad MensajeRecibidoPrivado
CREATE TABLE PreguntaEfectuadaChatPrivado (
	id_mensaje_privado INTEGER PRIMARY KEY NOT NULL UNIQUE,
	pregunta TEXT NOT NULL,
	respondido BOOLEAN CHECK (respondido IN (0, 1)) NOT NULL,

	FOREIGN KEY(id_mensaje_privado) REFERENCES MensajeRecibidoPrivado(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

--	Relación: PreguntaEfectuadaChatGrupal
--	Representa: Representa el atributo compuesto "pregunta_efectuada" del
--							subtipo de entidad MensajeRecibidoGrupal
CREATE TABLE PreguntaEfectuadaChatGrupal (
	id_mensaje_grupal INTEGER PRIMARY KEY NOT NULL UNIQUE,
	pregunta TEXT NOT NULL,
	respondido BOOLEAN CHECK (respondido IN (0, 1)) NOT NULL,

	FOREIGN KEY(id_mensaje_grupal) REFERENCES MensajeRecibidoPrivado(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Dato
CREATE TABLE Dato (
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
	fecha_creacion DATE NOT NULL DEFAULT (DATE('now','unixepoch'))
);

-- Relación: DatoTexto
-- Descripción: Representa una especialización del tipo Dato que contiene datos
--				de tipo texto
CREATE TABLE DatoTexto (
	id INTEGER PRIMARY KEY NOT NULL,
	texto TEXT NOT NULL,

	FOREIGN KEY(id) REFERENCES Dato(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: DatoArchivo
-- Descripción: Representa una especialización del tipo Dato que contiene datos
--				de diferentes tipos dentro de los datos multimedia admitidos
CREATE TABLE DatoArchivo (
	id INTEGER PRIMARY KEY NOT NULL,
	tipo TIPO_DATOARCHIVO NOT NULL, -- CHECK(tipo IN ('imagen','video','audio', 'nota_voz', 'nota_video', 'animacion', 'documento', 'sticker')),
	ruta_archivo TEXT,
	file_id TEXT,
	mime_type TEXT,

	FOREIGN KEY(id) REFERENCES Dato(id)
);

-- Relación: DatoArchivoSticker
-- Descripción: Representa una especialización del tipo DatoArchivo que
--							contiene los datos de un sticker de Telegram
CREATE TABLE DatoArchivoSticker (
	id INTEGER PRIMARY KEY NOT NULL,
	emoji TEXT,
	conjunto TEXT NOT NULL,
	tipo TIPO_STICKER,

	FOREIGN KEY(id) REFERENCES DatoArchivo(id) ON DELETE RESTRICT ON UPDATE RESTRICT
	-- id debe referenciar un tipo de DatoArchivo cuyo tipo sea sticker
);

-- Relación: DatoContacto
-- Descripción: Representa una especialización del tipo Dato que
--							contiene los datos de un contacto enviado
CREATE TABLE DatoContacto (
	id INTEGER PRIMARY KEY NOT NULL,
	telefono TEXT NOT NULL,
	nombre TEXT NOT NULL,
	apellidos TEXT,
	id_usuario INTEGER,
	vcard TEXT,

	FOREIGN KEY(id) REFERENCES Dato(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: DatoContacto
-- Descripción: Representa una especialización del tipo Dato que
--							contiene los datos de una localización o avenida enviada
CREATE TABLE DatoLocalizacion (
	id INTEGER PRIMARY KEY NOT NULL,
	longitud REAL NOT NULL,
	latitud REAL NOT NULL,
	titulo TEXT,
	direccion TEXT,
	id_cuadrante TEXT,
	tipo_cuadrante TEXT,

	FOREIGN KEY(id) REFERENCES Dato(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Concepto
CREATE TABLE Concepto (
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE
);

-- Relación: ConceptoPregunta
-- Descripción: Representa el atributo compuesto y múltiple del tipo de entidad
--							Concepto
-- Nota: El atributo id guarda una relación transitiva con la clave primaria,
--				no obstante, se desiste de normalizar a la FN3 puesto que no
--				se considera que la normalización traiga ningún beneficio REVISAR
CREATE TABLE ConceptoPregunta (
	pregunta TEXT PRIMARY KEY NOT NULL UNIQUE,
	resumen_pregunta TEXT NOT NULL,
	tipo TEXT,
	id INTEGER NOT NULL,

	UNIQUE(resumen_pregunta, tipo),
	FOREIGN KEY(id) REFERENCES Concepto(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Comunicado
CREATE TABLE Comunicado (
	id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE,
	fecha_envio DATE NOT NULL,
	--anclar BOOLEAN CHECK(anclar IN (0,1)) DEFAULT 0,
	id_docente INTEGER NOT NULL,

	FOREIGN KEY(id_docente) REFERENCES Usuario(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
-- Relación Foro_Usuario
-- Descripción: Representa el tipo de interrelación entre la relación Foro y
--				Usuario
CREATE TABLE Foro_Usuario (
	id_chat_foro INTEGER NOT NULL,
	id_usuario INTEGER NOT NULL,
	ban BOOLEAN CHECK (ban IN (0,1)),
	n_avisos INTEGER CHECK (n_avisos IS NULL OR n_avisos >= 0),
	 --CHECK(NOT EXISTS(SELECT id FROM Usuario WHERE Usuario.id=id_usuario AND Usuario.tipo=1) OR (ban IS NULL AND n_avisos IS NULL)),
	 -- EXISTS(SELECT id FROM Usuario WHERE Usuario.id=id_usuario AND Usuario.tipo=1) => ban IS NULL AND n_avisos IS NULL
	 -- Para los usuarios docentes, los campos "ban" y "n_avisos" deben de estar a NULL

	PRIMARY KEY(id_chat_foro, id_usuario),
	UNIQUE(id_chat_foro, id_usuario),
	FOREIGN KEY(id_chat_foro) REFERENCES Foro(id_chat) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_usuario) REFERENCES Usuario(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Dato_Mensaje
-- Descripción: Representa el tipo de interrelación entre los tipos de entidades
--				Dato y Mensaje
CREATE TABLE Dato_Mensaje (
	id_dato INTEGER PRIMARY KEY NOT NULL,
	id_mensaje INTEGER NOT NULL,

	FOREIGN KEY(id_dato) REFERENCES Dato(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_mensaje) REFERENCES Mensaje(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Dato_Comunicado
-- Descripción: Representa el tipo de interrelación entre los tipos de entidades
--				Dato y Comunicado
CREATE TABLE Dato_Comunicado (
	id_dato INTEGER PRIMARY KEY NOT NULL,
	id_comunicado INTEGER NOT NULL,

	FOREIGN KEY(id_dato) REFERENCES Dato(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_comunicado) REFERENCES Comunicado(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Dato_Concepto
-- Descripción: Representa el tipo de interrelación entre los tipos de entidades
--				Dato y Concepto
CREATE TABLE Dato_Concepto (
	id_dato INTEGER NOT NULL,
	id_concepto INTEGER NOT NULL,

	PRIMARY KEY(id_dato, id_concepto),
	UNIQUE(id_dato, id_concepto),
	FOREIGN KEY(id_dato) REFERENCES Dato(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_concepto) REFERENCES Concepto(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);

-- Relación: Comunicado_Foro
-- Descripción: Representa el tipo de interrelación existente entre los tipos
--				de entidad Comunicado y Foro
CREATE TABLE Comunicado_Foro (
	id_comunicado INTEGER NOT NULL,
	id_chat_foro INTEGER NOT NULL,

	PRIMARY KEY(id_comunicado, id_chat_foro),
	UNIQUE(id_comunicado, id_chat_foro),
	FOREIGN KEY(id_comunicado) REFERENCES Comunicado(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
	FOREIGN KEY(id_chat_foro) REFERENCES Foro(id_chat) ON DELETE RESTRICT ON UPDATE RESTRICT
);
