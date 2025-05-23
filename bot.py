from typing import List
from botbuilder.core import ActivityHandler, TurnContext, ConversationState, UserState, MessageFactory
from botbuilder.dialogs import DialogSet, WaterfallDialog, WaterfallStepContext, DialogTurnResult
from botbuilder.dialogs.prompts import TextPrompt, PromptOptions, ChoicePrompt, ConfirmPrompt
from botbuilder.dialogs.choices import Choice  
from botbuilder.dialogs.prompts import PromptValidatorContext
from botbuilder.schema import ChannelAccount
from sharepoint_helper import buscar_estudiante_por_id, mapear_campos, actualizar_registro_por_title, traducir_a_campos_sharepoint
import re
from botbuilder.dialogs.choices import ListStyle
import logging
from datetime import datetime, timezone
import random

# Configura logging
logging.basicConfig(level=logging.DEBUG)

# Definición de tipos de caso y subcasos
tipos_de_caso = {
    "Académico": ["Cambio de grupo", "Revisión de nota", "Homologación", "Cambio de pensum"],
    "Financiero": ["Solicitud de beca", "Revisión de factura", "Deuda pendiente", "Error de pago"],
    "Técnico": ["Falla en plataforma", "Error en matrícula", "Acceso denegado", "Problema con el correo"],
    "Administrativo": ["Cambio de carrera", "Reingreso", "Certificado académico", "Carné universitario"],
    "Otro": ["Consulta general", "Sugerencia", "Queja"]
}

# Configuración de casos manejados
casos_config = {
    "Académico": {
        "Cambio de pensum": {
            "tipo_gestion": "CONSULTA_SHAREPOINT",
            "descripcion": "Vamos a revisar tu semestre para indicarte los pasos correctos para el cambio de pensum.",
            "consulta": {
                "campo": "Semestre",
                "condicion": "<6",
                "respuesta_si": {
                    "mensaje": (
                        "✅ ¡Excelente! Como estás en **semestre menor a 6**, puedes hacer el cambio de pensum de forma directa y sencilla. Aquí te explico cómo hacerlo paso a paso:\n\n"
                        "1️⃣ Ingresa al siguiente enlace oficial: https://ficticia.edu/cambio-pensum\n\n"
                        "2️⃣ Completa el formulario con tus datos personales y académicos. Asegúrate de que toda la información esté actualizada y sin errores.\n\n"
                        "3️⃣ Adjunta tu historial académico en formato PDF. Puedes descargarlo desde el portal de estudiantes.\n\n"
                        "4️⃣ Revisa bien toda la información antes de enviar y haz clic en 'Enviar solicitud'.\n\n"
                        "5️⃣ Una vez enviada, revisa tu correo institucional frecuentemente. Allí recibirás la confirmación o instrucciones adicionales si es necesario.\n\n"
                        "Si tienes dudas o necesitas ayuda con algún paso, estoy aquí para orientarte. 📩"
                    )

                },
                "respuesta_no": {
                    "mensaje": (
                        "⚠️ Como estás en **semestre 6 o superior**, el cambio de pensum requiere una revisión personalizada con tu jefe de carrera. Para ello, sigue estos pasos detalladamente:\n\n"
                        "1️⃣ Ingresa al portal de citas: https://ficticia.edu/citas-jefecarrera\n\n"
                        "2️⃣ Selecciona tu carrera en el listado desplegable y escoge un horario disponible que te funcione.\n\n"
                        "3️⃣ Confirma la cita y toma nota de la fecha y hora asignada.\n\n"   
                        "4️⃣ El día de la cita, presenta una justificación académica clara (por ejemplo: razones de organización curricular, materias pendientes, doble titulación, etc.).\n\n"
                        "Recuerda ser puntual y llevar toda la documentación necesaria. Si tienes preguntas antes de la cita, puedo ayudarte a prepararte. 📝"
                    )
                }
            },
            "seguimiento": {
                "pregunta": "¿Lograste gestionar el cambio de pensum?",
                "respuesta_si": "📝 Perfecto. El cambio ha sido registrado.",
                "respuesta_no": {"mensaje": "⏳ Vamos a escalar tu caso con una reunión personalizada.", "escalar": True}
            },
            "registro": {
                "Titulo": "Problema académico respecto al cambio de pensum",
                "TipoDeCaso": "Académico",
                "SubtipoDeCaso": "Cambio de pensum",
                "Descripcion": "",
                "FechaSolicitud":"",
                "Estado":"",
                "Urgencia":"Baja",
                "AsignadoA":"",
                "Notas":"",
                "FechaSeguimiento":"",
                "EnlaceReunion": "",
                "IDInteraccionBot":"",
                "RequiereEscalamiento": False,
                "NotasResolución":""
            }
        }
    },
    "Financiero": {
        "Solicitud de beca": {
            "tipo_gestion": "GUÍA_AUTOGESTIÓN",
            "descripcion": "Aquí están los pasos para solicitar una beca institucional.",
            "guia": (
                "🎓 **Pasos para solicitar la beca:**\n\n"
                "1. Accede a https://ficticia.edu/becas\n\n"
                "2. Llena el formulario de solicitud\n\n"
                "3. Adjunta los documentos requeridos\n\n"
                "4. Envíalo antes del 10 de junio\n\n"
                "5. Revisa tu correo institucional frecuentemente\n\n"
            ),
            "seguimiento": {
                "pregunta": "¿Finalizaste correctamente el proceso de solicitud de beca?",
                "respuesta_si": "👍 Perfecto. Ahora debes esperar el resultado por correo.",
                "respuesta_no": "📨 Te recomiendo contactar soporte financiero si presentas dificultades."
            },
            "registro": {
                "TipoDeCaso": "Financiero",
                "SubtipoDeCaso": "Solicitud de beca",
                "Estado": "Autogestionado",
                "Urgencia": "Media",
                "RequiereEscalamiento": False
            }
        }
    },
    "Técnico": {
        "Problema con el correo": {
            "tipo_gestion": "DECISION_USUARIO",
            "descripcion": "Vamos a ayudarte con el problema en tu correo institucional.",
            "pregunta_usuario": {
                "pregunta": "¿Has cambiado tu contraseña en los últimos 3 meses?",
                "respuesta_si": {
                    "mensaje": (
                        "🔧 Como ya cambiaste tu contraseña recientemente:\n\n"
                        "1. Ve a https://ficticia.edu/soporte\n\n"
                        "2. Crea un ticket indicando 'Correo institucional bloqueado'\n\n"
                        "3. Adjunta evidencia del error\n\n"
                        "4. Te responderán al correo alternativo"
                    )
                },
                "respuesta_no": {
                    "mensaje": (
                        "🔑 Para recuperar el acceso a tu correo institucional, sigue estos pasos con calma:\n\n"
                        "1️⃣ Entra al siguiente enlace: https://ficticia.edu/cambiar-clave\n\n"
                        "2️⃣ Escribe tu usuario institucional (sin @ficticia.edu).\n\n"
                        "3️⃣ Elige una nueva contraseña que sea segura. Asegúrate de incluir mayúsculas, números y símbolos para que cumpla con los requisitos.\n\n"
                        "4️⃣ Confirma la nueva contraseña y guarda los cambios.\n\n"
                        "5️⃣ Espera al menos 15 minutos. Este tiempo es necesario para que el sistema actualice tu acceso.\n\n"
                        "6️⃣ Luego, intenta ingresar nuevamente a tu correo con la nueva contraseña.\n\n"
                        "Si después de esto sigues teniendo problemas, avísame para ayudarte a escalar el caso. 💬"
                    )

                }
            },
            "seguimiento": {
                "pregunta": "¿Lograste recuperar el acceso a tu correo?",
                "respuesta_si": "✅ Excelente. Me alegra haberte ayudado.",
                "respuesta_no": "📅 Vamos a agendar una reunión con soporte técnico."
            },
            "registro": {
                "AsignadoA":"Coordinador Técnico",
                "TipoDeCaso": "Técnico",
                "SubtipoDeCaso": "Problema con el correo",
                "Estado": "En seguimiento",
                "Urgencia": "Alta",
                "RequiereEscalamiento": True
            }
        }
    }
}

class EchoBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, user_state: UserState):
        super().__init__()
        self.conversation_state = conversation_state
        self.user_state = user_state
        self.dialog_state = conversation_state.create_property("DialogState")
        self.user_profile = user_state.create_property("UserProfile")
        self.dialogs = DialogSet(self.dialog_state)

        # Añadir prompts al DialogSet
        self.dialogs.add(TextPrompt("TextPrompt"))
        self.dialogs.add(ConfirmPrompt("ConfirmPrompt", default_locale="es-ES"))
        self.dialogs.add(ChoicePrompt("ChoicePrompt"))

        # Definir el WaterfallDialog con ID "main_dialog"
        self.dialogs.add(
            WaterfallDialog(
                "main_dialog",
                [
                    self.request_name_step,
                    self.request_id_step,
                    self.request_case_type_step,
                    self.request_subcase_step,
                    self.handle_case_selection_step,
                    self.seguimiento_step,
                    self.follow_up_step,
                    self.finalize_step,
                ],
            )
        )
            
        # Diálogos específicos para cada tipo de gestión
        self.dialogs.add(WaterfallDialog("consulta_sharepoint_dialog", [
            self.consulta_sharepoint_step,
        ]))
        self.dialogs.add(WaterfallDialog("guia_autogestion_dialog", [
            self.guia_autogestion_step,
            self.seguimiento_step
        ]))
        self.dialogs.add(WaterfallDialog("decision_usuario_dialog", [
            self.decision_usuario_step,
            self.respuesta_decision_usuario_step,
            self.seguimiento_step
        ]))
        
    async def respuesta_decision_usuario_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])
        respuesta = step_context.result

        if respuesta is True:
            mensaje = case_config["pregunta_usuario"]["respuesta_si"]["mensaje"]
        else:
            mensaje = case_config["pregunta_usuario"]["respuesta_no"]["mensaje"]

        await step_context.context.send_activity(MessageFactory.text(mensaje))
        user_profile["case_response"] = mensaje
        await self.user_profile.set(step_context.context, user_profile)
        return await step_context.next(None)


    async def on_turn(self, turn_context: TurnContext):
        logging.debug(f"Procesando turno en on_turn, actividad: {turn_context.activity.text}")
        dialog_context = await self.dialogs.create_context(turn_context)
        logging.debug(f"Diálogo activo: {dialog_context.active_dialog}")
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    async def on_members_added_activity(self, members_added: List[ChannelAccount], turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity("👋 ¡Hola! Bienvenido(a) al asistente virtual de la U. Estoy aquí para ayudarte con lo que necesites. 😊")
                dialog_context = await self.dialogs.create_context(turn_context)  # Use create_context
                logging.debug("Enviando mensaje de bienvenida y solicitando nombre")
                await dialog_context.begin_dialog("main_dialog")
                return

    async def on_message_activity(self, turn_context: TurnContext):
        dialog_context = await self.dialogs.create_context(turn_context)
        logging.debug(f"Actividad de mensaje recibida: {turn_context.activity.text}")
        if dialog_context.active_dialog is None:
            logging.debug("Iniciando main_dialog desde mensaje")
            await dialog_context.begin_dialog("main_dialog")
        else:
            logging.debug(f"Continuando diálogo: \n{dialog_context.active_dialog}")
            await dialog_context.continue_dialog()
        await self.conversation_state.save_changes(turn_context)
        await self.user_state.save_changes(turn_context)

    # Paso 1: Solicitar nombre
    async def request_name_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en request_name_step: {user_profile}")

        if "name" not in user_profile:
            return await step_context.prompt(
                "TextPrompt",
                PromptOptions(
                    prompt=MessageFactory.text("😊 ¿Cuál es tu nombre completo?"),
                    retry_prompt=MessageFactory.text("Por favor, ingresa tu nombre completo.")
                )
            )
        
        return await step_context.next(user_profile["name"])

    # Paso 2: Solicitar ID y validar
    async def request_id_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en request_id_step: {user_profile}")

        user_profile["name"] = step_context.result
        await self.user_profile.set(step_context.context, user_profile)

        if "id" not in user_profile:
            return await step_context.prompt(
                "TextPrompt",
                PromptOptions(
                    prompt=MessageFactory.text(f"{user_profile['name']}, por favor ingresa tu ID de estudiante."),
                    retry_prompt=MessageFactory.text("Por favor, ingresa un número de identificación válido.")
                )
            )
        
        return await step_context.next(user_profile["id"])

    # Paso 3: Seleccionar tipo de caso
    async def request_case_type_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en request_case_type_step: {user_profile}")
        if isinstance(step_context.result, str):
            id_input = step_context.result.strip()
            if not re.match(r"^\d+$", id_input):
                await step_context.context.send_activity("El ID debe contener solo números. Por favor, intenta de nuevo.")
                return await step_context.prompt(
                    "TextPrompt",
                    PromptOptions(prompt=MessageFactory.text(f"{user_profile['name']}, ingresa tu ID de estudiante (solo números)."))
                )
            user_profile["id"] = id_input
            await self.user_profile.set(step_context.context, user_profile)

        return await step_context.prompt(
            "ChoicePrompt",
            PromptOptions(
                prompt=MessageFactory.text(f"{user_profile['name']}, dime en qué área estás teniendo dificultades para poder ayudarte mejor:"),
                choices=[Choice(key) for key in tipos_de_caso.keys()]
            )
        )

    # Paso 4: Seleccionar subcaso
    async def request_subcase_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en request_subcase_step: {user_profile}")
        user_profile["case_type"] = getattr(step_context.result, "value", step_context.result)
        await self.user_profile.set(step_context.context, user_profile)

        subcases = tipos_de_caso.get(user_profile["case_type"], [])
        return await step_context.prompt(
            "ChoicePrompt",
            PromptOptions(
                prompt=MessageFactory.text(f"{user_profile['name']}, selecciona el subcaso para {user_profile['case_type']}:"),
                choices=[Choice(subcase) for subcase in subcases],
                style=ListStyle.hero_card
            )
        )

    # Paso 5: Manejar la selección del caso
    async def handle_case_selection_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en handle_case_selection_step: {user_profile}")
        user_profile["subcase"] = getattr(step_context.result, "value", step_context.result)
        await self.user_profile.set(step_context.context, user_profile)

        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])
        if not case_config:
            await step_context.context.send_activity(
                f"{user_profile['name']}, lo siento, el caso '{user_profile['subcase']}' no está implementado aún. Por favor, contacta al soporte."
            )
            return await step_context.end_dialog()

        if case_config["tipo_gestion"] != "CONSULTA_SHAREPOINT":
            await step_context.context.send_activity(case_config["descripcion"])

        
        if case_config["tipo_gestion"] == "CONSULTA_SHAREPOINT":
            return await step_context.begin_dialog("consulta_sharepoint_dialog")
        elif case_config["tipo_gestion"] == "GUÍA_AUTOGESTIÓN":
            return await step_context.begin_dialog("guia_autogestion_dialog")
        elif case_config["tipo_gestion"] == "DECISION_USUARIO":
            return await step_context.begin_dialog("decision_usuario_dialog")
        return await step_context.next(None)

    # Paso 6: Procesar el caso según tipo de gestión
    async def process_case_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        return await step_context.next(None)

    # Consulta SharePoint (Cambio de pensum)
    async def consulta_sharepoint_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en consulta_sharepoint_step: {user_profile}")
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])

        try:
            logging.debug(f"Consultando SharePoint para ID: {user_profile['id']}")
            student_data = buscar_estudiante_por_id(user_profile['id'])
            if not student_data:
                await step_context.context.send_activity(f"{user_profile['name']}, no se encontró información para tu ID. Por favor, verifica e intenta de nuevo.")
                return await step_context.end_dialog()

            mapped_data = mapear_campos(student_data)
            semestre = int(mapped_data.get("Semestre", 0))
            condicion = case_config["consulta"]["condicion"]

            if eval(f"{semestre} {condicion}"):
                await step_context.context.send_activity(
                    MessageFactory.text(case_config["consulta"]["respuesta_si"]["mensaje"])
                )
                user_profile["case_response"] = case_config["consulta"]["respuesta_si"]["mensaje"]
            else:
                await step_context.context.send_activity(
                    MessageFactory.text(case_config["consulta"]["respuesta_no"]["mensaje"])
                )
                user_profile["case_response"] = case_config["consulta"]["respuesta_no"]["mensaje"]

            await self.user_profile.set(step_context.context, user_profile)
            return await step_context.next(None)

        except Exception as e:
            logging.error(f"Error en consulta SharePoint: {str(e)}")
            await step_context.context.send_activity(f"{user_profile['name']}, error al consultar la información: {str(e)}")
            return await step_context.end_dialog()

    # Guía de autogestión (Solicitud de beca)
    async def guia_autogestion_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en guia_autogestion_step: {user_profile}")
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])

        await step_context.context.send_activity(case_config["guia"])
        user_profile["case_response"] = case_config["guia"]
        await self.user_profile.set(step_context.context, user_profile)
        return await step_context.next(None)

    # Decisión del usuario (Problema con el correo)
    async def decision_usuario_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en decision_usuario_step: {user_profile}")
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])

        return await step_context.prompt(
            "ConfirmPrompt",
            PromptOptions(
                prompt=MessageFactory.text(case_config["pregunta_usuario"]["pregunta"]),
                retry_prompt=MessageFactory.text("Por favor, responde 'sí' o 'no'.")
            )
        )
    async def seguimiento_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en seguimiento_step: {user_profile}")
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])
        logging.debug(f"Case config en seguimiento_step: {case_config}")

        # Si es la primera vez que se llama a este paso, mostrar el ConfirmPrompt
        if step_context.result is None:
            logging.debug("Primera llamada a seguimiento_step, mostrando ConfirmPrompt")
            return await step_context.prompt(
                "ConfirmPrompt",
                PromptOptions(
                    prompt=MessageFactory.text(
                        f"{user_profile['name']}, {case_config['seguimiento']['pregunta']}"
                    ),
                    retry_prompt=MessageFactory.text("Por favor, selecciona 'Sí' o 'No'.")
                )
            )

        # Procesar la respuesta del usuario (ConfirmPrompt devuelve un booleano)
        es_respuesta_afirmativa = step_context.result
        logging.debug(f"Respuesta de ConfirmPrompt recibida: {es_respuesta_afirmativa}, Tipo: {type(es_respuesta_afirmativa)}")

        return await step_context.next(es_respuesta_afirmativa)

    async def follow_up_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"VALOR REAL DE RESPUESTA EN FOLLOW_UP_STEP: {step_context.result}, Tipo: {type(step_context.result)}")
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])

        # Manejar el caso en que step_context.result es None
        if step_context.result is None:
            logging.error(f"Error: step_context.result es None en follow_up_step. User profile: {user_profile}")
            es_respuesta_afirmativa = False
        else:
            es_respuesta_afirmativa = step_context.result is True

        logging.debug(f"Resultado procesado - Valor: {step_context.result}, Tipo: {type(step_context.result)}, Afirmativo: {es_respuesta_afirmativa}")

        if es_respuesta_afirmativa:
            await step_context.context.send_activity(case_config["seguimiento"]["respuesta_si"])
        else:
            if isinstance(case_config["seguimiento"]["respuesta_no"], dict):
                await step_context.context.send_activity(case_config["seguimiento"]["respuesta_no"]["mensaje"])
                if case_config["seguimiento"]["respuesta_no"].get("escalar", False):
                    await step_context.context.send_activity(
                        f"{user_profile['name']}, tu caso será escalado. Pronto recibirás más información."
                    )
            else:
                await step_context.context.send_activity(case_config["seguimiento"]["respuesta_no"])

        return await step_context.next(step_context.result)

    async def finalize_step(self, step_context: WaterfallStepContext) -> DialogTurnResult:
        user_profile = await self.user_profile.get(step_context.context, lambda: {})
        logging.debug(f"User profile en finalize_step: {user_profile}")
        case_config = casos_config.get(user_profile["case_type"], {}).get(user_profile["subcase"])

        try:
            logging.debug(f"Registrando caso en SharePoint para ID: {user_profile['id']}")

            ahora = datetime.now().strftime("%Y-%m-%d")
            id_interaccion = f"BOT-{random.randint(100000,999999)}"
            solucionado = step_context.result is True
            
            logging.debug(f"Solucionado: {solucionado}")

            # Construcción completa
            campos_legibles = {
                "Título": case_config["registro"].get("Titulo", f"Caso de {user_profile['subcase']}"),
                "TipoDeCaso": case_config["registro"]["TipoDeCaso"],
                "SubtipoDeCaso": case_config["registro"]["SubtipoDeCaso"],
                "Descripción": case_config.get("descripcion", ""),
                "FechaSolicitud": ahora,
                "Estado": "Finalizado" if solucionado else "En seguimiento",
                "Urgencia": "Media" if not solucionado else "Baja",
                "AsignadoA": None if solucionado else case_config["registro"].get("AsignadoA", "Coordinador Académico"),
                "Notas": None,
                "FechaSeguimiento": ahora,
                "EnlaceReuniónVirtual": None if solucionado else "https://teams.microsoft.com/l/meetup-join/5001e145-e78d-41db-875f-1f494ba0bc46",
                "IDInteracciónBot": id_interaccion,
                "RequiereEscalamiento": not solucionado,
                "NotasResolución": "Se indicó al usuario que realizara los pasos sugeridos para resolver su caso.",
            }

            # Eliminar claves con valor None
            campos_legibles = {k: v for k, v in campos_legibles.items() if v is not None}

            # Convertir a campos internos SharePoint
            campos_sharepoint = traducir_a_campos_sharepoint(campos_legibles)

            # Asegurar que los booleanos estén como tipo bool real
            if "field_20" in campos_sharepoint:
                campos_sharepoint["field_20"] = bool(campos_sharepoint["field_20"])

            logging.debug(f"Campos actualizados para SharePoint: {campos_sharepoint}")
            actualizar_registro_por_title(user_profile["id"], campos_sharepoint)

            await step_context.context.send_activity(
                f"{user_profile['name']}, tu caso ha sido registrado exitosamente. ✅"
            )

        except Exception as e:
            logging.error(f"Error al registrar en SharePoint: {str(e)}")
            await step_context.context.send_activity(
                f"{user_profile['name']}, error al registrar el caso: {str(e)}"
            )

        await self.user_profile.delete(step_context.context)
        return await step_context.end_dialog()