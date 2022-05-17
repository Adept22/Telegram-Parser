import asyncio, logging, telethon
import entities, exceptions, services

async def _member_media_process(chat_phone: 'entities.TypeChatPhone', member: 'entities.TypeMember', user: 'telethon.types.TypeUser'):
    async with services.ChatPhoneClient(chat_phone) as client:
        try:
            async for photo in client.iter_profile_photos(user):
                photo: 'telethon.types.TypePhoto'

                media = entities.MemberMedia(internalId=photo.id, member=member, date=photo.date.isoformat())

                try:
                    media.save()
                except exceptions.RequestException as ex:
                    logging.error(f"Can't save member {member.id} media. Exception: {ex}.")
                else:
                    logging.info(f"Member {member.id} media saved.")

                    size = next(((size.type, size.size) for size in photo.sizes if isinstance(size, telethon.types.PhotoSize)), ('', None))
                    tg_media = telethon.types.InputPhotoFileLocation(
                        id=photo.id,
                        access_hash=photo.access_hash,
                        file_reference=photo.file_reference,
                        thumb_size=size[0]
                    )
                    extension = telethon.utils.get_extension(photo)

                    try:
                        await media.upload(client, tg_media, size[1], extension)
                    except exceptions.RequestException as ex:
                        logging.error(f"Can\'t upload member {member.id} media. Exception: {ex}.")
                    else:
                        logging.info(f"Member {member.id} media uploaded.")
        except (TypeError, KeyError, ValueError, telethon.errors.RPCError) as ex:
            logging.error(f"Can't get member {member.id} media.")

def member_media_process(chat_phone, member: 'entities.TypeMember', user: 'telethon.types.TypeUser'):
    asyncio.set_event_loop(asyncio.new_event_loop())

    asyncio.run(_member_media_process(chat_phone, member, user))
