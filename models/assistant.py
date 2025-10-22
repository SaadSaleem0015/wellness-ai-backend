from tortoise.models import Model
from tortoise import fields

class Assistant(Model):
    id = fields.IntField(pk=True)
    vapi_assistant_id = fields.CharField(max_length=255, null=True)
    user = fields.ForeignKeyField("models.User", related_name="assistant")
    company = fields.ForeignKeyField("models.Company", related_name="assistants")

    name = fields.CharField(max_length=255)
    provider = fields.CharField(max_length=255)
    first_message = fields.CharField(max_length=255)
    model = fields.CharField(max_length=255)
    systemPrompt = fields.TextField()
    knowledge_base = fields.ManyToManyField(
        "models.Knowledgebase", related_name="knowledgebase"
    )  
    leadsfile = fields.JSONField(null=True)  
    temperature = fields.FloatField(null=True)
    maxTokens = fields.IntField(null=True)
    transcribe_provider = fields.CharField(max_length=255, null=True)
    transcribe_language = fields.CharField(max_length=255, null=True)
    transcribe_model = fields.CharField(max_length=255, null=True)
    voice_provider = fields.CharField(max_length=255, null=True)
    voice = fields.CharField(max_length=255, null=True)
    forwardingPhoneNumber = fields.CharField(max_length=255, null=True)
    endCallPhrases = fields.JSONField(null=True)  
    attached_Number = fields.CharField(max_length=255, null=True, default=None)
    vapi_phone_uuid = fields.CharField(max_length=255, null=True, default=None)
    success_evalution = fields.TextField(null=True)
    voice_model = fields.TextField(null=True,default="eleven_multilingual_v2")
    tools = fields.JSONField(null=True)  
    # add_voice_id_manually = fields.BooleanField(default=False)
    # voice_id = fields.CharField(max_length=255, null=True)
