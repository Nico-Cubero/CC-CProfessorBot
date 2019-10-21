#	C-ProfessorBot
##	Proyecto de la asignatura Cloud Computing Fundamentos y estructura

Proyecto llevado a cabo en la asignatura **Cloud Computing. Fundamentos y estructura** del **Máster de Ingeniería Informática** en la Universidad de Granada consistente en la aplicación de herramientas y metodologías de **Cloud Computing** para el despliegue de una ampliación sobre el sistema servidor **CProfessorBot** desarrollado como Trabajo de Fin de Grado en la Universidad de Córdoba durante el curso 18/19, el cual puede ser consultado en el siguiente ![link](https://github.com/Nico-Cubero/C-ProfessorBot)

####	Descripción del Proyecto

El proyecto pretende ampliar las características del sistema CProfessorBot, en el cual, el procesamiento de todas las peticiones de todos sus usuarios recaía en un único sistema servidor monolítico *multithreading*.

Esta ampliación, pretende reestructurar la arquitectura del servidor a una arquitectura Cloud Computing, de forma que se permita desplegar de forma independiente cada uno de los módulos funcionales del sistema original en los diferentes microservicios con el objetivo de aumentar las capacidades del sistema:

- Aumento de la disponibilidad del sistema: Se espera que esta arquitectura permita extender el uso del sistema a un mayor número de usuarios y a un mayor número de asignaturas (la implementación actual únicamente soporta una única asignatura por servidor).

- Aumento de las capacidades de cómputo del sistema servidor, especialmente en los módulos que implementan los algoritmos de procesamiento del lenguaje natural y los algoritmos de búsqueda y recuperación de las bases de datos, cuyo coste se incrementa sustancialmente con el tamaño de la información a procesar y, en su versión actual, son ejecutados por algún hilo del servidor monolítico.

Por su parte, originalmente **C-ProfessorBot** es un sistema servidor de un bot docente e inteligente que permite implementar un asistente conversacional, chatbot o simplemente bot que, interoperando por medio de la plataforma de mensajería Telegram, interactúa con los usuarios, bien en un chat grupal de alumn@s, o bien en chats privados para recibir consultas teóricas formuladas en lenguaje natural y tratar de responder a las mismas en estos chats. El sistema incluye otras funcionalidades como la capacidad de evaluación de la temática de conversación de los mensajes emitidos por el alumnado, la gestión de los foros de docencia, recopilación de información sobre el uso del sistema y de los foros docentes por parte del alumnado, etc.

En esta página se desarrollará la documentación oficial de este proyecto. La documentación se irá agregando conforme se vaya agregando el sistema.
