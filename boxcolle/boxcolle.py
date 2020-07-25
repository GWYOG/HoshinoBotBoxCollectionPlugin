from nonebot import on_command, MessageSegment

from hoshino import R, Service, priv
from hoshino.typing import CQEvent
from hoshino.modules.priconne import chara
from .dao.collesettingsqlitedao import ColleSettingDao
from .dao.collerequestsqlitedao import ColleRequestDao
from .dao.boxcollesqlitedao import BoxColleDao

import datetime, random, os, csv
from PIL import Image, ImageDraw, ImageFont
from time import sleep

sv = Service('boxcolle', bundle='pcrbox统计', help_='''
一键box统计 | 在配置完box统计参数后使用此指令，机器人会自动私聊公会成员统计其box
----------
设置box统计 <数据库名> <统计对象> <备注> <统计的角色名(逗号分隔)> | 统计对象参数目前支持填写"all"(全部成员) 或"allE@xxx@yyy"(全部成员除去xxx和yyy) 或"@xxx@yyy"(xxx和yyy)
----------
查看box统计 [数据库名] | 查看指定数据库的统计情况
----------
查看box统计 [数据库名] <@qq> | 查看指定用户的角色星级
----------
查看box统计 [数据库名] <角色名> | 查看指定角色的星级分布
----------
查看box统计 [数据库名] <@qq> <角色名> | 查看指定用户的指定角色星级
----------
删除box数据 [数据库名] <@qq> | 删除指定用户的box信息
----------
删除box数据 [数据库名] <角色名> | 删除数据库中指定角色的所有录入信息
----------
查看box数据库名 [数据库名] | 查看所有存放box的数据库的名称
----------
查看已统计角色 [数据库名] | 查看已经录入数据库的所有角色名称
----------
导出box统计表 [数据库名] | 从数据库中导出csv格式的box统计表格到后台
----------
发送box统计图 [数据库名] | 机器人发送图片形式的box统计表格到群里，需要机器人能够发图并且服务器装有"simsun.ttc"字体才能使用此功能
'''.strip())


class CommandConfirmer:    
    def __init__(self, max_valid_time):
        self.last_command_time = datetime.datetime(2020, 4, 17, 0, 0, 0, 0)
        self.max_valid_time = max_valid_time

    def check(self):
        now_time = datetime.datetime.now()
        delta_time = now_time - self.last_command_time
        return delta_time.seconds <= self.max_valid_time
    
    def record_command_time(self):
        self.last_command_time = datetime.datetime.now()
        
    def has_command_wait_to_confirm(self):
        return self.last_command_time != datetime.datetime(2020, 4, 17, 0, 0, 0, 0)
        
    def reset(self):
        self.last_command_time = datetime.datetime(2020, 4, 17, 0, 0, 0, 0)


MAX_VALID_TIME = 30
SEND_INTERVAL = 0.5
command_confirmer = CommandConfirmer(MAX_VALID_TIME)
broadcast_list= []
broadcast_msg = ''

VALID_STAR = ['0', '1', '2', '3', '4', '5', '6']


@on_command('测试用随机录入')
async def random_box_input(session):
    db = ColleRequestDao()
    r = db._find_by_id(session.event.user_id)
    if r==None:
        await session.send('您暂时还没收到公会的box统计请求')
        return
    s = r[2]
    sList = s.split(',')
    box = []
    for item in sList:
        name = item.strip()
        if not is_valid_name(name):
            await session.send(f'录入box失败，请按正确的格式填写')
            return
        box.append(name)
    db = BoxColleDao()
    for i in range(10):
        uid = int(random.random()*10000000000)
        for chara_name in box:
            db._update_or_insert(uid, r[0], chara_name2chara_id(chara_name), chara_name, '4' if random.random()>0.5 else '5')
    await session.send(f'随机测试box录入完毕!') 


@on_command('录入box')
async def box_input(session):
    db = ColleRequestDao()
    r = db._find_by_id(session.event.user_id)
    if r==None:
        await session.send('您暂时还没收到公会的box统计请求')
        return
    
    s = session.current_arg
    if s=='':
        msg = f'''
请按格式输入以下角色的星级(可单次或分多次输入):\n
{r[2]}\n
备注:\n
{r[1]}\n
输入格式:\n
在需要输入的人物名后面直接填写星级数。\n比如想录入"狼,狗"的星级，\n则输入"录入box 狼4,狗5"\n如果没有这个人物，则填0\n
下方文本供复制修改使用:
'''.strip()
        await session.send(msg)
        await session.send(f'录入box {r[2]}')
    else:
        sList = s.split(',')
        box = {}
        for item in sList:
            item = item.strip()
            name = item[0:-1]
            star = item[-1]
            if not is_valid_name(name) or star not in VALID_STAR:
                await session.send(f'录入box失败，请按正确的格式填写')
                return
            box[name] = star
        db = BoxColleDao()
        for key in box.keys():
            db._update_or_insert(session.event.user_id, r[0], chara_name2chara_id(str(key)), str(key), box[key])
        await session.send(f'box录入完毕!')
        user_card = await get_user_card(session.bot, r[3], session.event.user_id)
        await session.bot.send_group_msg(group_id=r[3], message=f'{user_card}完成了box录入')


def normalize_str(s):
    sList = s.replace('，',',').split(',')
    return ', '.join([s.strip() for s in sList])


def chara_name2chara_id(name):
    return chara.name2id(name.strip())


def is_valid_name(name):
    return chara_name2chara_id(name)!=chara.UNKNOWN


def is_valid_input(s):
    sList = s.split(',')
    for name in sList:
        if not is_valid_name(name):
            return name, False
    return '', True


async def get_user_card_dict(bot, group_id):
    mlist = await bot.get_group_member_list(group_id=group_id)
    d = {}
    for m in mlist:
        d[m['user_id']] = m['card'] if m['card']!='' else m['nickname']
    return d


async def get_user_card(bot, group_id, user_id):
    mlist = await bot.get_group_member_list(group_id=group_id)
    for m in mlist:
        if m['user_id'] == user_id:
            return m['card'] if m['card']!='' else m['nickname']
    return str(user_id)


def uid2card(uid, user_card_dict):
    return str(uid) if uid not in user_card_dict.keys() else user_card_dict[uid]


def is_uid_in_blacklist(uid, blacklist, blacklist_on):
    return False if not blacklist_on else uid in blacklist


async def get_broadcast_list_str(bot, ev: CQEvent, collect_target_str):
    try:
        sList = collect_target_str.split('@')
        broadcast_list = []
        if sList[0]=='hoshino':
            return ''
        elif sList[0]=='hoshinoE':
            return ''
        elif sList[0]=='yobot':
            return ''
        elif sList[0]=='yobotE':
            return ''
        elif sList[0].startswith('all'):
            blacklist_on = sList[0]=='allE'
            mlist = await bot.get_group_member_list(group_id=ev.group_id, self_id=ev.self_id)
            for m in mlist:
                if m['user_id'] != ev.self_id and not is_uid_in_blacklist(str(m['user_id']), sList[1:], blacklist_on):  
                    broadcast_list.append(str(m['user_id']))
            return ','.join(broadcast_list)
        elif sList[0]=='':
            return ','.join(sList[1:])
        else:
            await bot.send(ev, '统计对象格式错误') 
    except:
       await bot.send(ev, '统计对象格式错误')   


def parse_message(msg):
    s = ''
    for seg in msg:
        if seg.type == 'text' and not str(seg).isspace():
            s += str(seg)
        if seg.type == 'at':
            s += '@' + str(seg.data['qq'])
    s = ' '.join(s.split())
    return s


@sv.on_prefix(('设置box统计', '设定box统计'))
async def set_box_collection(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '抱歉，您非管理员，无此指令使用权限')
    s = parse_message(ev.message)
    if len(s)==0:
        await bot.finish(ev, '请在指令后输入正确参数，发送"帮助pcrbox统计"查看更多\n例如"设置box统计 巨蟹座公会战 allE@xxx@yyy 会战前能达到的星级 狼,狗,黑骑"')
    s = s.lstrip().split(' ', 3)
    if len(s)!=4 or '' in s:
        await bot.finish(ev, '参数格式错误，输入"帮助pcrbox统计"查看正确参数格式')
    broadcast_list_str = await get_broadcast_list_str(bot, ev, s[1])
    chara_name_str = normalize_str(s[3])
    unknown_name, valid = is_valid_input(chara_name_str)
    if not valid:
        await bot.finish(ev, f'检测到输入参数中存在未知人物名"{unknown_name}"，请重新输入')
    db = ColleSettingDao()
    db._update_or_insert_by_id(ev.group_id, s[0], broadcast_list_str, s[2], chara_name_str)
    command_confirmer.reset()
    await bot.send(ev, '设定box统计项目完毕!')  

    
@sv.on_prefix('确认发送')
async def confirm_broadcast(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '抱歉，您非管理员，无此指令使用权限')
    if command_confirmer.check():
        db1 = ColleSettingDao()
        r = db1._find_by_id(ev.group_id)
        db_name, broadcast_list_str, detail, collection_setting = r[0], r[1], r[2], r[3]
        broadcast_list = broadcast_list_str.split(',')
        user_card = await get_user_card(bot, ev.group_id, ev.user_id)
        db2 = ColleRequestDao()
        command_confirmer.reset()
        await bot.send(ev, f'即将开始广播，此过程大概需要{int(len(broadcast_list)*SEND_INTERVAL)+1}s完成，请耐心等待')
        for uid in broadcast_list:
            db2._update_or_insert_by_id(int(uid), ev.group_id, db_name, detail, collection_setting)
            await bot.send_private_msg(user_id=int(uid), message=f'您好~群{ev.group_id}的管理员{user_card}({ev.user_id})正在统计公会成员的box，请输入"录入box"并根据指示向机器人录入您的box~')
            sleep(SEND_INTERVAL)
        await bot.send(ev, f'广播成功!已向{len(broadcast_list)}人私聊发送box统计请求')
    elif command_confirmer.has_command_wait_to_confirm():
        await bot.send(ev, f'确认超时，请在{MAX_VALID_TIME}s内完成确认')
    else:
        await bot.send(ev, '未找到需要确认的指令')


@sv.on_prefix(('一键box统计', '一键统计box'))
async def box_collect(bot, ev: CQEvent):
    try:
        if not priv.check_priv(ev, priv.ADMIN):
            await bot.send(ev, '抱歉，您非管理员，无此指令使用权限')
            return
        db1 = ColleSettingDao()
        r = db1._find_by_id(ev.group_id)
        if r == None:
            await bot.send(ev, '请先使用"设置box统计"指令设置box统计参数')
            return
        db_name, broadcast_list_str, detail, collection_setting = r[0], r[1], r[2], r[3]
        broadcast_list = broadcast_list_str.split(',')
        user_card = await get_user_card(bot, ev.group_id, int(broadcast_list[0]))
        msg_part = '' if len(broadcast_list)==1 else f'等{len(broadcast_list)}人'
        msg = f'''
准备向{user_card}{msg_part}私聊统计box，当前参数如下:\n
存放统计结果的数据库: {db_name}\n
此次统计的相关说明: {detail}\n
需要统计的人物名: {collection_setting}\n\n
确认无误后请输入"确认发送"完成广播，如需修改参数，请使用"设定box统计"指令
'''.strip()
        command_confirmer.record_command_time()
        await bot.send(ev, msg)
    except:
        await bot.send(ev, '一键统计失败，请重试')
        
        
@sv.on_prefix('删除box数据')
async def delete_data_from_db(bot, ev:CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '抱歉，您非管理员，无此指令使用权限')
    s = parse_message(ev.message).strip().split(' ')
    s = list(filter(None, s))
    if len(s)==1:
        db = ColleSettingDao()
        r = db._find_by_id(ev.group_id)
        curr_db_name = '' if r==None else r[0]
        s_complemented = [curr_db_name]
        s_complemented.extend(s)
    else:
        s_complemented = s
    
    if len(s_complemented)==2 and s_complemented[1].startswith('@'):
        db_name = s_complemented[0]
        user_id = s_complemented[1][1:]
        db = BoxColleDao()
        db._delete_by_user_id(user_id, db_name)
        user_card = await get_user_card(bot, ev.group_id, user_id)
        await bot.send(ev, f'已将{user_card}录入的数据从{db_name}数据库中删除')
    elif len(s_complemented)==2 and is_valid_name(s_complemented[1]):
        db_name = s_complemented[0]
        chara_id = chara_name2chara_id(s_complemented[1])
        db = BoxColleDao()
        db._delete_by_chara_id(chara_id, db_name)
        await bot.send(ev, f'已将{s_complemented[1]}的全部录入信息从{db_name}数据库中删除')
    else:
        await bot.send(ev, '参数格式错误，请重新输入')


@sv.on_prefix('查看box数据库名')
async def get_collection_db_list(bot, ev: CQEvent):
    db1 = BoxColleDao()
    db_list = db1._get_recorded_dbname_list()
    db2 = ColleSettingDao()
    r = db2._find_by_id(ev.group_id)
    curr_db_name = '' if r==None else r[0]
    sorted_db_list = sorted(db_list, key=lambda d:1 if d[0]==curr_db_name else 0)
    await bot.send(ev, f'此群共有以下{len(sorted_db_list)}个box数据库(第一行为当前数据库):\n' + '\n'.join(sorted_db_list))


@sv.on_prefix('查看已统计角色')
async def get_collection_db_list(bot, ev: CQEvent):
    s = ev.message.extract_plain_text()
    if len(s)==0:
        db = ColleSettingDao()
        r = db._find_by_id(ev.group_id)
        db_name = '' if r==None else r[0]
    else:
        db_name = s
    db = BoxColleDao()
    recorded_charaname_list = db._get_recorded_charaname_list(db_name)
    msg = f'{db_name}数据库已统计下列{len(recorded_charaname_list)}名角色的星级:\n' + ', '.join(recorded_charaname_list)
    await bot.send(ev, msg)


@sv.on_prefix(('查看box', '查看box统计'))
async def get_collection_result(bot, ev: CQEvent):
    try:
        s = parse_message(ev.message).strip().split(' ')
        s = list(filter(None, s))
        if len(s)==0 or (len(s)==1 and (s[0].startswith('@') or is_valid_name(s[0]))) or (len(s)==2 and s[0].startswith('@') and is_valid_name(s[1])):
            db = ColleSettingDao()
            r = db._find_by_id(ev.group_id)
            curr_db_name = '' if r==None else r[0]
            s_complemented = [curr_db_name]
            s_complemented.extend(s)
        else:
            s_complemented = s  

        if len(s_complemented) == 1:
            db = BoxColleDao()
            uid_list = db._get_recorded_uid_list(s_complemented[0])
            user_card_dict = await get_user_card_dict(bot, ev.group_id)
            msg = f'{s_complemented[0]}数据库共{len(uid_list)}人录入了box，他们是:\n' + '\n'.join([uid2card(uid, user_card_dict) for uid in uid_list])
            await bot.send(ev, msg)
        elif len(s_complemented) == 2:
            if s_complemented[1].startswith('@'):
                uid = int(s_complemented[1][1:])
                user_card = await get_user_card(bot, ev.group_id, uid)
                db = BoxColleDao()
                charname_list = db._get_recorded_charaname_list(s_complemented[0])
                star_list = [db._find_by_primary_key(uid, s_complemented[0], chara_name2chara_id(i)) for i in charname_list]
                box_str = ','.join([f' {charname_list[i]}{star_list[i]}x'for i in range(len(charname_list)) if star_list[i]!='']).lstrip()
                msg = f'{s_complemented[0]}数据库中{user_card}录入的box是:\n' + box_str
                await bot.send(ev, msg)
            elif is_valid_name(s_complemented[1]):
                chara_id = chara_name2chara_id(s_complemented[1])
                db = BoxColleDao()
                uid_dict = db._find_by_chara_id(chara_id, s_complemented[0])
                star_list = sorted(set(uid_dict.values()), reverse = True)
                msg_part = ''
                user_card_dict = await get_user_card_dict(bot, ev.group_id)
                for star in star_list:
                    card_list = [uid2card(uid, user_card_dict) for uid in uid_dict.keys() if uid_dict[uid]==star]
                    msg_part += f'{star}x: (共{len(card_list)}人)\n'
                    msg_part += ', '.join(card_list) + '\n'
                msg = f'{s_complemented[0]}数据库中录入的{s_complemented[1]}的星级情况为:\n' + msg_part.strip()
                await bot.send(ev, msg)    
        elif len(s_complemented) == 3:
            uid = int(s_complemented[1][1:])
            chara_id = chara_name2chara_id(s_complemented[2])
            db = BoxColleDao()
            star = db._find_by_primary_key(uid, s_complemented[0], chara_id)
            user_card = await get_user_card(bot, ev.group_id, uid)
            msg = f'{s_complemented[0]}数据库中{user_card}{s_complemented[2]}的星级为: {star}x'
            await bot.send(ev, msg)    
    except:
        await bot.send(ev, '参数格式错误，请重试')


@sv.on_prefix('导出box统计表')
async def write_box_colle_to_csv(bot, ev: CQEvent):
    try:
        if not priv.check_priv(ev, priv.ADMIN):
            await bot.finish(ev, '抱歉，您非管理员，无此指令使用权限')
        s = ev.message.extract_plain_text()
        if len(s)==0:
            db = ColleSettingDao()
            r = db._find_by_id(ev.group_id)
            db_name = '' if r==None else r[0]
        else:
            db_name = s
        
        file_path = os.path.normcase(os.path.expanduser(f'~/.hoshino/box_{ev.group_id}.csv'))
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            db = BoxColleDao() 
            charaname_list = db._get_recorded_charaname_list(db_name)
            row0 = ['']
            row0.extend(charaname_list)
            writer.writerow(row0)
    
            uid_list = db._get_recorded_uid_list(db_name)
            user_card_dict = await get_user_card_dict(bot, ev.group_id)
            for uid in uid_list:
                row = [uid2card(uid, user_card_dict)]
                for chara_name in charaname_list:
                    star = db._find_by_primary_key(uid, db_name, chara_name2chara_id(chara_name))
                    if star == '':
                        star_str = star
                    elif star == '0':
                        star_str = '-'
                    else:
                        star_str = f'{star}x'
                    row.append(star_str)
                writer.writerow(row)
            f.close()
        await bot.send(ev, f'{db_name}数据库的box统计表已导出到\n{file_path}')
    except:
        await bot.send(ev, f'导出失败')


def get_max_char_amount(s, draw, fnt, max_length):
    max_amount = 0
    for i in range(len(s)):
        width, height = draw.textsize(s[0:(i+1)], font = fnt)
        if width > max_length:
            return max_amount
        else:
            max_amount += 1
    return max_amount

    
@sv.on_prefix('发送box统计图')
async def send_box_colle_pic(bot, ev: CQEvent):
    try:
        s = ev.message.extract_plain_text()
        if len(s)==0:
            db = ColleSettingDao()
            r = db._find_by_id(ev.group_id)
            db_name = '' if r==None else r[0]
        else:
            db_name = s
    
        db = BoxColleDao()
        charaname_list = db._get_recorded_charaname_list(db_name)
        uid_list = db._get_recorded_uid_list(db_name)
        user_card_dict = await get_user_card_dict(bot, ev.group_id)
    
        im = Image.open(os.path.normcase('hoshino/modules/boxcolle/pic/table_base.png'))
        draw = ImageDraw.Draw(im)
        fnt = ImageFont.truetype("simsun.ttc", 16, encoding="unic")
        if len(charaname_list) > 31:
            await bot.send(ev, '抱歉，由于统计的角色过多，图片无法生成，请期待后续版本的优化')
            return
        if len(uid_list) > 30:
            await bot.send(ev, '统计人数超过30人，图片生成失败')
            return
        for i in range(len(charaname_list)):
            width, height = draw.textsize(charaname_list[i], font = fnt)
            draw.text((153+i*46-width/2,30), charaname_list[i], fill=(0, 0 ,0), font=fnt)
        for i in range(len(uid_list)):
            card = uid2card(uid_list[i], user_card_dict)
            card_trunc = card[0:get_max_char_amount(card, draw, fnt, 80)]
            draw.text((43, 54+i*23), card_trunc, fill=(0, 0 ,0), font=fnt)
        for i in range(len(uid_list)):
            for j in range(len(charaname_list)):
                star = db._find_by_primary_key(uid_list[i], db_name, chara_name2chara_id(charaname_list[j]))
                if star == '':
                    star_str = star
                elif star == '0':
                    star_str = '-'
                else:
                    star_str = f'{star}x'    
                draw.text((148+j*46, 54+i*23), star_str, fill=(0, 0 ,0), font=fnt)
        pic_path = os.path.normcase(f'hoshino/modules/boxcolle/pic/box_{ev.group_id}.png')
        im.save(pic_path)
        pic = MessageSegment.image(f'file:///{os.path.abspath(pic_path)}')   
        await bot.send(ev, pic)
    except:
        await bot.send(ev, '发送失败，请检查机器人是否能发图或服务器是否未安装"simsun.ttc"字体')
