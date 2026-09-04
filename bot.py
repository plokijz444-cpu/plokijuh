import discord
from discord.ext import commands
import datetime
import re

intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용 읽기 권한
intents.members = True          # 서버 멤버 및 역할 관리 권한

bot = commands.Bot(command_prefix="!", intents=intents)

# ⚠️ 감지할 욕설/금지어 목록
BAD_WORDS = ["느금", "느금마", "금마", "니엄마", "니애미", "ㄴㄱㅁ", "ㄴㅇㅁ", "니앰", "앰창", "your mom", "니애비", "느개비", "느금빠", "ㄴㄱㅃ", "금빠", "창년", "섹스", "색스", "색's", "섹's", "섹s", "색s", "운지", "응디", "운디", "응지", "보지", "자지", "좆물", "봊물", "보지물", "자지물", "정액"]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("------ 자동 검열 + 수동 제재(!제재) + 3시간 누적 시스템 가동 중 ------")

# ⚙️ 공통 제재 처리 함수 (자동/수동 모두 이 로직을 거칩니다)
async def punish_member(guild, member, channel, reason_text):
    # 관리자나 서버 주인은 제재에서 제외
    if member.guild_permissions.administrator:
        return

    # 1. 유저의 현재 전과 단계 파악하기
    current_crime_level = 0
    current_role = None

    for role in member.roles:
        match = re.match(r"전과\s*(\d+)범", role.name)
        if match:
            current_crime_level = int(match.group(1))
            current_role = role
            break

    # 2. 전과 단계 업그레이드 (최대 20범)
    next_crime_level = current_crime_level + 1
    if next_crime_level > 20:
        next_crime_level = 20

    # 3. 새 역할 찾기 및 교체
    next_role_name = f"전과 {next_crime_level}범"
    next_role = discord.utils.get(guild.roles, name=next_role_name)

    if next_role:
        try:
            if current_role:
                await member.remove_roles(current_role)
            await member.add_roles(next_role)
        except discord.Forbidden:
            await channel.send("❌ 봇의 역할 순위가 낮아 전과 역할을 부여하지 못했습니다.")
            return
    else:
        await channel.send(f"❌ 서버에 `{next_role_name}` 역할이 존재하지 않습니다.")
        return

    # 4. 💡 3시간 단위 누적 공식 적용 (기본 1시간 + 2범부터 3시간씩 추가)
    timeout_hours = 1 + (next_crime_level - 1) * 3
    duration = datetime.timedelta(hours=timeout_hours)

    # 5. 타임아웃 실행 및 안내 메시지 전송
    try:
        await member.timeout(duration, reason=f"{reason_text} (누적 {next_crime_level}회)")
        
        # 알림 메시지
        embed = discord.Embed(title="🚨사용자 경고 및 제재 안내", color=0xff0000)
        embed.add_field(name="제재 대상", value=member.mention, inline=True)
        embed.add_field(name="현재 상태", value=f"**{next_role_name}** 승급", inline=True)
        embed.add_field(name="타임아웃 처벌", value=f"**{timeout_hours}시간** 동안 말하기 금지", inline=False)
        embed.set_footer(text="경고가 누적될 때마다 처벌 시간이 3시간씩 늘어납니다.")
        
        await channel.send(embed=embed)
        
    except discord.Forbidden:
        await channel.send("❌ 봇에게 멤버 제재(타임아웃) 권한이 없습니다.")

@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        return

    # 1. 🚨 [자동 욕설/금지어 검열 기능]
    clean_content = message.content.replace(" ", "")
    if any(bad_word in clean_content for bad_word in BAD_WORDS):
        try:
            await message.delete()
        except discord.Forbidden:
            print("메시지를 삭제할 권한이 없습니다.")

        # 공통 제재 함수 호출
        await punish_member(message.guild, message.author, message.channel, "금지어 사용 적발")
        return

    # 2. 👋 [인사 반응 기능]
    user_msg = message.content.strip()
    if user_msg == "안녕하세요" or user_msg == "안녕":
        await message.channel.send(f"반가워요, {message.author.mention}님! 오늘도 좋은 하루 되세요! 😊")

    # 다른 명령어들(!제재 등)이 정상 작동하도록 처리
    await bot.process_commands(message)

# 3. 🛠️ [수동 제재 명령어]
@bot.command(name="제재")
@commands.has_permissions(moderate_members=True)  # 멤버 제재 권한이 있는 관리자만 사용 가능
async def manual_punish(ctx, member: discord.Member):
    await ctx.send(f"⚙️ {member.mention} 유저에 대한 수동 제재를 진행합니다.")
    await punish_member(ctx.guild, member, ctx.channel, "관리자에 의한 수동 제재")

# 수동 제재 명령어 에러 처리 (유저 멘션을 안 했거나 권한이 없을 때)
@manual_punish.error
async def manual_punish_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ 사용법: `!제재 @유저멘션` 형태로 입력해주세요.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다. (멤버 제재 권한 필요)")
    else:
        await ctx.send(f"❌ 에러가 발생했습니다: {error}")

bot.run("MTU0Mzk1NTM3MzUzNzYyODI3MA.GZ8fvt.Gt50XjmbWg9-JpGTjgh1WPMIF3THyV_wo-u4uk")