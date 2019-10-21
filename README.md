#	C-ProfessorBot
##	Proyecto de la asignatura Cloud Computing Fundamentos y estructura

Proyecto llevado a cabo en la asignatura **Cloud Computing. Fundamentos y estructura** del **Máster de Ingeniería Informática** en la Universidad de Granada consistente en la aplicación de herramientas y metodologías de **Cloud Computing** para el despliegue de una ampliación sobre el sistema servidor **CProfessorBot** desarrollado como Trabajo de Fin de Grado en la Universidad de Córdoba durante el curso 18/19, el cual puede ser consultado en el siguiente ![link](https://github.com/Nico-Cubero/C-ProfessorBot)

####	Descripción del Proyecto

El proyecto pretende ampliar las características del sistema CProfessorBot, en el cual, el procesamiento de todas las peticiones de todos sus usuarios recaía en un único sistema servidor monolítico *multithreading*.

Esta ampliación, pretende reestructurar la arquitectura del servidor a una arquitectura basada en **microservicios**, de forma que se permita desplegar de forma independiente cada uno de los módulos funcionales del sistema original en los diferentes microservicios con el objetivo de aumentar las capacidades del sistema:

- Aumento de la disponibilidad del sistema: Se espera que esta arquitectura permita extender el uso del sistema a un mayor número de usuarios y a un mayor número de asignaturas (la implementación actual únicamente soporta una única asignatura por servidor).

- Aumento de las capacidades de cómputo del sistema servidor, especialmente en los módulos que implementan los algoritmos de procesamiento del lenguaje natural y los algoritmos de búsqueda y recuperación de las bases de datos, cuyo coste se incrementa sustancialmente con el tamaño de la información a procesar y, en su versión actual, son ejecutados por algún hilo del servidor monolítico.

El sistema originalmente se podría descomponer funcionalmente de la siguiente forma:

- Módulo de comunicación: Se ocupa de recibir las peticiones emitidas por los usuarios al asistente y de remitir esta información al núcleo del sistema para su tratamiento. También se encarga de enviar las respuestas generadas por el sistema a sus usuarios. Este módulo se comunica directamente con los servidores de la plataforma Telegram gracias a su API.

- Núcleo del sistema: Organizar el funcionamiento del sistema coordinando al resto de módulos.

- Módulo de gestión de información: Gestiona y almacena toda la información necesaria: Información de los usuarios, foros de docencia, mensajes enciados o recibidos y la información teórica almacenada.

- Módulo de procesamiento del lenguaje natural: Se encarga de aplicar todos los algoritmos de procesamiento del lenguaje natural en los procesos en los que se requiere (análisis de los conceptos preguntados en las pregunta y evaluación de la temática de conversación de los mensajes principalmente) y devolver una respuesta.

Por su parte, CProfessorBot constituye un asistente conversacional, chatbot o simplemente bot docente e inteligente que interopera por medio de la plataforma de mensajería **Telegram**, para interactuar con los usuarios, bien en un chat grupal de alumn@s, o bien en chats privados, para recibir consultas teóricas formuladas en lenguaje natural y tratar de responder a las mismas en estos chats. El sistema incluye otras funcionalidades como la capacidad de evaluación de la temática de conversación de los mensajes emitidos por el alumnado, la gestión de los foros de docencia, recopilación de información sobre el uso del sistema y de los foros docentes por parte del alumnado, etc.
