import asyncio
from discord_typings import ActionRowData, ButtonComponentData, GuildCreateData, GuildData, GuildDeleteData, InteractionData, PartialChannelData, ReadyData, RoleData, Snowflake
from discord_typings.interactions.receiving import ComponentGuildInteractionData
from nextcore.gateway import ShardManager
from nextcore.http import BotAuthentication, HTTPClient
from logging import getLogger
from base64 import b64encode
from nextcore.common.errors import RateLimitedError

logger = getLogger("nextbox.worker")


class WorkerBot:
    def __init__(self, authentication: BotAuthentication, http_client: HTTPClient) -> None:
        self.authentication = authentication
        self.http_client = http_client
        self.shard_manager: ShardManager | None = None
        self.guilds: dict[Snowflake, GuildData] = {}

    async def connect(self):
        self.shard_manager = ShardManager(self.authentication, 1, self.http_client)
    
        self.shard_manager.event_dispatcher.add_listener(self.on_ready, "READY")
        self.shard_manager.event_dispatcher.add_listener(self.on_guild_create, "GUILD_CREATE")
        self.shard_manager.event_dispatcher.add_listener(self.on_guild_delete, "GUILD_DELETE")
        self.shard_manager.event_dispatcher.add_listener(self.on_interaction, "INTERACTION_CREATE")

        await self.shard_manager.connect()

    async def on_ready(self, ready_data: ReadyData):
        logger.info("Logged in as %s", ready_data["user"]["username"])
        self.guilds.clear()

    async def on_guild_create(self, guild_data: GuildCreateData):
        self.guilds[guild_data["id"]] = guild_data
    async def on_guild_delete(self, guild_data: GuildDeleteData):
        del self.guilds[guild_data["id"]]

    async def close(self):
        assert self.shard_manager
        await self.shard_manager.close()

    @property
    def capacity(self):
        return 10 - len(self.guilds)

    async def cleanup_guilds(self, *, force: bool = False):
        try:
            if force:
                await asyncio.gather(*[self.http_client.delete_guild(self.authentication, guild["id"], wait=False) for guild in self.guilds.values()])
            else:
                raise NotImplementedError()
        except RateLimitedError:
            pass

    async def on_interaction(self, interaction: ComponentGuildInteractionData):
        custom_id = interaction["data"]["custom_id"]

        if custom_id == "delete_guild":
            await self.http_client.delete_guild(self.authentication, interaction["guild_id"])
        elif custom_id == "toggle_admin":
            guild = self.guilds[interaction["guild_id"]]
            roles = guild["roles"]

            for role in roles:
                if role["name"] == "Admin":
                    assert "user" in interaction["member"]
                    if role["id"] in interaction["member"]["roles"]:
                        await self.http_client.remove_guild_member_role(self.authentication, guild["id"], interaction["member"]["user"]["id"], role["id"])
                    else:
                        await self.http_client.add_guild_member_role(self.authentication, guild["id"], interaction["member"]["user"]["id"], role["id"])


    async def create_guild(self):
        # Create the guild
        with open("server_icon.png", "rb") as f:
            raw_icon = f.read()
        icon_header = "data:image/png;base64,"
        icon = icon_header + b64encode(raw_icon).decode("utf-8")

        info_channel: PartialChannelData = {
            "id": 1,
            "name": "info",
            "type": 0
        }
        testing_channel: PartialChannelData = {
            "id": 2,
            "name": "testing",
            "type": 0
        }
        voice_testing_channel: PartialChannelData = {
            "id": 3,
            "name": "Voice Testing",
            "type": 2
        }
        default_role: RoleData = {
            "id": 4,
            "name": "@everyone",
            "color": 0,
            "hoist": False,
            "position": 0,
            "permissions": "1071698533953", # Pretty much the default minus ping @everyone
            "managed": False,
            "mentionable": False 

        }
        admin_role: RoleData = {
            "id": 5,
            "name": "Admin",
            "color": 0x00FFFF,
            "hoist": False,
            "position": 0,
            "permissions": "8", # Admin
            "managed": False,
            "mentionable": True

        }
        guild = await self.http_client.create_guild(self.authentication, "NextBox guild", icon=icon, channels=[
            info_channel,
            testing_channel,
            voice_testing_channel
        ], roles=[default_role, admin_role])

        channels = await self.http_client.get_guild_channels(self.authentication, guild["id"])

        fetched_info_channel = channels[0]
        
        # Control message
        give_admin_button: ButtonComponentData = {
            "type": 2,
            "style": 3,
            "custom_id": f"toggle_admin",
            "label": "Toggle admin"
        }
        delete_guild_button: ButtonComponentData = {
            "type": 2,
            "style": 4,
            "custom_id": f"delete_guild",
            "label": "Delete guild"
        }
        components: ActionRowData = {
            "type": 1,
            "components": [
                give_admin_button,
                delete_guild_button
            ]
        }
        await self.http_client.create_message(self.authentication, fetched_info_channel["id"], content="Admin panel", components=[components])

        invite = await self.http_client.create_channel_invite(self.authentication, fetched_info_channel["id"], max_uses=0, max_age=0)

        return f"https://discord.gg/{invite['code']}"
