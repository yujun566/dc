# -*- coding: utf-8 -*-
"""
가강전(가장 강한 전장) 클랜 디스코드 봇  —  dc.py  (버튼 패널 통합본)
  - 슬래시 명령어 100개 제한을 우회하기 위해 모든 기능을 "기능 레지스트리"로 등록하고
    버튼 패널(검색 / help / 카테고리 / 내 정보 / 랭킹 / 티밍)에서 실행
  - 모든 결과는 비공개(ephemeral) 메시지로 본인만 볼 수 있음
  - 관리 기능은 관리자 역할이 있는 사람만 검색·실행 가능
  - 클랜 데이터(전투력, 전적, 랭킹표, 칭호, 직책 등)는 전부 관리자만 수정 가능

설치:  pip install -U discord.py
실행:  python dc.py
"""
import os, re, random, sqlite3, time, asyncio, datetime, hashlib, base64, math, urllib.parse
from typing import Optional, Callable, Any

import discord
from discord import app_commands
from discord.ext import commands

# ───────────────────────────── 설정 ─────────────────────────────
TOKEN = "여기에_봇_토큰_입력"
DB_PATH = "dc_bot_v2.db"
GAME_LINK = "https://www.roblox.com/games/10449761463/The-Strongest-Battlegrounds"

TIERS = [(0, "브론즈", "🥉"), (1000, "실버", "🥈"), (3000, "골드", "🥇"), (6000, "플래티넘", "💠"),
         (10000, "다이아", "💎"), (20000, "마스터", "👑"), (40000, "그랜드마스터", "🔥"), (80000, "S급 히어로", "🌟")]
POSITIONS = ["단장", "부단장", "간부", "정예", "일반", "신입"]

# 캐릭터 데이터 — 자유롭게 수정 가능
CHARS = {
    "사이타마": dict(type="근접 화력", diff="쉬움", tier="S", skills=["연속 펀치", "진심 펀치(차지)", "도약 펀치", "테이블 뒤집기"],
                 counter="차지 모션 보이면 옆으로 대시 후 뒤잡기", tip="진심 펀치는 아껴두고 상대 울트 빠진 뒤에 쓰기"),
    "진심 사이타마": dict(type="각성 폭딜", diff="쉬움", tier="S", skills=["진심 연속 펀치", "진심 사이드스텝", "진심 테이블", "진심 펀치 Ω"],
                    counter="게이지 끝날 때까지 거리 벌리기", tip="각성 직후 가장 가까운 적부터 순삭"),
    "가로우": dict(type="근접 콤보", diff="보통", tier="S", skills=["유수암쇄권", "사냥 찌르기", "수상 발차기", "장력 격파"],
               counter="콤보 첫타를 가드하고 반격", tip="M1 4타 후 유수암쇄권 캔슬 연습"),
    "괴인 가로우": dict(type="각성 광역", diff="보통", tier="S", skills=["괴인 난타", "충격파 발차기", "회피 반격", "괴인 포효"],
                  counter="광역기 범위 밖에서 원거리 견제", tip="회피 반격은 상대 M1 타이밍에 맞춰 사용"),
    "겐노스": dict(type="원거리 화력", diff="보통", tier="A", skills=["기관포", "블리츠 샷", "점프 킥", "소각포"],
               counter="원거리기 쿨타임에 붙어서 콤보", tip="소각포는 벽 쪽으로 몰고 사용"),
    "각성 겐노스": dict(type="각성 폭격", diff="보통", tier="A", skills=["연속 포격", "부스트 러시", "초고열 소각", "오버드라이브"],
                  counter="부스트 러시 후딜에 반격", tip="오버드라이브는 1v1보다 다수전에서 효율"),
    "소닉": dict(type="기동 암살", diff="어려움", tier="A", skills=["질풍 베기", "폭발 수리검", "사중 분신", "소닉 스텝"],
              counter="분신은 본체 이동 경로 예측", tip="스텝으로 빠지고 수리검으로 마무리"),
    "플래시 소닉": dict(type="각성 초고속", diff="어려움", tier="A", skills=["섬광 참격", "잔상 난무", "질주", "최종 베기"],
                  counter="가드 유지 후 잔상 끝나면 잡기", tip="최종 베기는 체력 30% 이하 적에게"),
    "메탈 배트": dict(type="근접 탱커", diff="쉬움", tier="B", skills=["풀스윙", "배트 투척", "근성 돌진", "지면 강타"],
                 counter="근성 버프 끝나는 타이밍 노리기", tip="피 낮을수록 강해지니 무리하지 말고 버티기"),
    "각성 메탈 배트": dict(type="각성 근성", diff="쉬움", tier="B", skills=["불꽃 풀스윙", "대지 분쇄", "근성 폭발", "홈런"],
                    counter="홈런 모션 때 뒤로 대시", tip="근성 폭발로 콤보 끊고 역습"),
    "아토믹 사무라이": dict(type="근접 검술", diff="보통", tier="A", skills=["아토믹 슬래시", "발도", "연속 베기", "검기 폭발"],
                     counter="발도 범위 바깥에서 유도", tip="발도는 상대 대시 끝 지점에 미리 깔기"),
    "각성 아토믹": dict(type="각성 일섬", diff="어려움", tier="A", skills=["무음 베기", "천참", "검풍", "일섬"],
                  counter="천참 전조 보이면 즉시 가드", tip="일섬은 가드 불가, 상대 회피 대시 뒤에"),
    "타츠마키": dict(type="원거리 염력", diff="보통", tier="S", skills=["염력 파쇄", "암석 투척", "사이코 쓰나미", "공중 띄우기"],
                counter="공중기 피하고 지상에서 붙기", tip="띄우기 → 암석 → 파쇄 기본 콤보"),
    "각성 타츠마키": dict(type="각성 광역", diff="어려움", tier="S", skills=["중력 붕괴", "파편 폭풍", "염력 감옥", "대지 융기"],
                    counter="감옥 걸리기 전에 거리 유지", tip="다수전에서 중력 붕괴로 한 번에 정리"),
    "스이류": dict(type="근접 무술", diff="보통", tier="B", skills=["공룡 발차기", "회전 축격", "연속 돌려차기", "비룡 낙하"],
               counter="돌려차기 후딜에 잡기", tip="축격으로 가드 깨고 연속 콤보"),
    "각성 스이류": dict(type="각성 격투", diff="보통", tier="B", skills=["진 공룡권", "폭풍 회전", "공중 연격", "최종 낙하"],
                  counter="공중 연격은 아래서 기다리기", tip="최종 낙하는 벽 콤보 마무리용"),
}
CHAR_LIST = list(CHARS)

TERMS = {
    "M1": "기본 공격(마우스 좌클릭). 보통 4타 콤보", "대시": "Q로 빠르게 이동, 쿨타임 있음", "울트": "각성/궁극기. 게이지가 차면 G로 발동",
    "티밍": "여러 명이 한 명을 집중 공격하는 비매너 플레이", "가드": "F로 방어. 잡기/가드불가기에는 뚫림", "가드 브레이크": "가드를 깨는 공격",
    "잡기": "가드를 무시하는 공격", "캔슬": "스킬 후딜을 다른 행동으로 끊는 테크닉", "벽콤": "벽에 몰아넣고 넣는 콤보", "램": "래그돌 상태(넉백 후 쓰러짐)",
    "후딜": "스킬 사용 후 생기는 경직", "선딜": "스킬 발동 전 준비 동작", "카운터": "상대 공격 타이밍에 맞춰 반격하는 기술", "리셋": "콤보 중 다시 처음부터 콤보 가능해지는 상황",
    "다운": "쓰러진 상태. 추가타 불가 구간", "히트박스": "공격 판정 범위", "핑": "서버 지연시간. 높을수록 렉", "서버 호핑": "다른 서버로 옮기기",
    "프라이빗 서버": "개인 서버. 친구끼리 연습용", "스폰킬": "리스폰 직후 공격하는 비매너", "트레이닝": "연습 모드", "콤보 익스텐더": "콤보를 늘려주는 스킬",
    "블록 스턴": "가드 성공 시 생기는 경직", "에어본": "띄우기 상태", "그라운드": "지상 상태", "오버헤드": "가드 위로 들어가는 공격", "백스텝": "뒤로 빠지는 대시",
    "ARG": "아토믹/가로우 류 약어 사용 예", "NPC": "봇/AI 적", "1v1": "일대일", "FFA": "자유 난전", "KD": "킬/데스 비율", "AFK": "자리 비움",
    "메타": "현재 가장 강한 전략/캐릭터", "너프": "하향 조정", "버프": "상향 조정", "패치": "게임 업데이트", "리워크": "스킬 전면 개편", "이모트": "감정표현 동작", "킬 스트릭": "연속 킬",
}
QUIZ = [
    ("가강전에서 가드 키는?", "F"), ("대시 키는?", "Q"), ("각성(울트) 키는?", "G"), ("여러 명이 한 명을 치는 걸 뭐라 할까?", "티밍"),
    ("사이타마 차지 기술 이름은?", "진심 펀치"), ("기본 공격을 영어 약어로?", "M1"), ("벽에 몰아 넣는 콤보는?", "벽콤"),
    ("가드를 무시하는 공격은?", "잡기"), ("스킬 사용 후 경직은?", "후딜"), ("다른 서버로 옮기는 행동은?", "서버 호핑"),
    ("가로우의 대표 기술 '유수○○권'?", "암쇄"), ("겐노스는 어떤 타입?", "원거리"), ("소닉의 분신 기술은?", "사중 분신"),
    ("메탈 배트는 피가 낮을수록?", "강해진다"), ("타츠마키의 공격 수단은?", "염력"), ("가드 성공 시 생기는 경직은?", "블록 스턴"),
    ("콤보 후딜을 끊는 테크닉은?", "캔슬"), ("리스폰 직후 공격하는 비매너는?", "스폰킬"), ("서버 지연시간을 뭐라 할까?", "핑"),
    ("현재 가장 강한 전략을 뭐라 할까?", "메타"), ("하향 조정은?", "너프"), ("상향 조정은?", "버프"), ("자유 난전 모드 약어는?", "FFA"),
    ("킬/데스 비율 약어는?", "KD"), ("공중에 띄워진 상태는?", "에어본"), ("연습 모드는?", "트레이닝"), ("개인 서버는?", "프라이빗 서버"),
    ("아토믹 사무라이의 무기는?", "검"), ("스이류의 대표 기술은?", "공룡 발차기"), ("플래시 소닉은 소닉의?", "각성"),
]
TIPS = ["대시 쿨 체크하고 접근", "상대 울트 게이지 보고 거리 유지", "벽콤 연습이 승률의 반", "티밍당하면 패널 🚨 버튼으로 클랜원 호출", "램 끊긴 서버는 바로 탈출",
        "가드 브레이크 타이밍 익히기", "콤보 끝에 반드시 거리 벌리기", "핑 150 넘으면 서버 호핑", "1v1 연습은 프라이빗 서버에서", "상대 캐릭터 스킬 쿨 암기"]
MEMES = ["아 티밍만 안 당했으면…", "렉이 아니라 내 실력이 문제", "울트 썼는데 빗나감 ㅋㅋ", "서버 옮기세요 제발", "소닉 유저 = 도망 전문", "진심 펀치 한 방이면 끝",
         "가드만 하다 게임 끝남", "메탈 배트 피 1로 역전함", "타츠마키한테 공중에서 삶", "내 핑 999 실화?"]
QUOTES = ["강함이란 하루아침에 얻어지는 게 아니다", "진정한 영웅은 도망치지 않는다", "100번 지면 101번 도전", "콤보는 손이 아니라 머리로", "패배는 데이터다",
          "티밍은 실력이 아니다", "오늘의 연습이 내일의 S급", "쫄지 마, 상대도 사람이다", "가드는 공격의 시작", "클랜은 혼자가 아니라는 증거"]
SHOP = [("경험치 부스트", 300, "다음 승리 전투력 2배 (관리자 확인용 표시)"), ("닉 색상권", 500, "역할 색상 변경 요청권"), ("칭호 변경권", 800, "칭호 변경 1회"),
        ("VIP 뱃지", 1500, "프로필에 ⭐ 표시"), ("전투력 보호권", 1000, "패배 시 전투력 감소 1회 면제"), ("행운의 부적", 200, "운세 재굴림 1회"),
        ("클랜 깃발", 2500, "명단 상단 📍 표시"), ("도박 보험", 400, "도박 실패 시 50% 환급 1회"), ("이름표", 100, "프로필 한 줄 소개"), ("황금 주사위", 1200, "황금 주사위 이모지")]
TZ = {"서울": 9, "도쿄": 9, "베이징": 8, "싱가포르": 8, "방콕": 7, "두바이": 4, "모스크바": 3, "파리": 1, "런던": 0, "뉴욕": -5, "시카고": -6, "덴버": -7,
      "LA": -8, "시드니": 10, "오클랜드": 12, "호놀룰루": -10}
UNITS = [("km", "m", 1000), ("m", "cm", 100), ("cm", "mm", 10), ("마일", "km", 1.609344), ("인치", "cm", 2.54), ("피트", "m", 0.3048), ("야드", "m", 0.9144),
         ("kg", "g", 1000), ("파운드", "kg", 0.45359237), ("온스", "g", 28.349523), ("톤", "kg", 1000), ("L", "mL", 1000), ("갤런", "L", 3.785411784),
         ("시간", "분", 60), ("분", "초", 60), ("일", "시간", 24), ("주", "일", 7), ("년", "일", 365), ("km/h", "m/s", 1 / 3.6), ("mph", "km/h", 1.609344),
         ("평", "㎡", 3.305785), ("에이커", "㎡", 4046.8564), ("헥타르", "㎡", 10000), ("MB", "KB", 1024), ("GB", "MB", 1024), ("TB", "GB", 1024),
         ("kcal", "J", 4184), ("마력", "W", 745.7), ("kW", "W", 1000), ("바이트", "비트", 8), ("달러", "센트", 100), ("만", "천", 10), ("억", "만", 10000),
         ("리", "km", 0.392727), ("자", "cm", 30.3), ("근", "g", 600), ("되", "L", 1.8), ("말", "L", 18), ("광년", "km", 9.4607e12), ("해리", "km", 1.852)]
COLORS = {"빨강": 0xE74C3C, "주황": 0xE67E22, "노랑": 0xF1C40F, "초록": 0x2ECC71, "청록": 0x1ABC9C, "파랑": 0x3498DB, "남색": 0x34495E, "보라": 0x9B59B6,
          "분홍": 0xFF69B4, "하양": 0xFFFFFF, "검정": 0x010101, "회색": 0x95A5A6, "금색": 0xFFD700, "은색": 0xC0C0C0, "하늘": 0x87CEEB, "민트": 0x98FF98,
          "와인": 0x722F37, "네이비": 0x000080, "라임": 0xBFFF00, "코랄": 0xFF7F50}
NOTICE_TPL = {"모집": ("📢 클랜원 모집", "가강전 클랜에서 함께할 클랜원을 모집합니다!\n조건: {내용}"), "점검": ("🔧 점검 안내", "{내용}"), "이벤트": ("🎉 이벤트", "{내용}"),
              "경고": ("⚠️ 경고", "{내용}"), "축하": ("🎊 축하합니다", "{내용}"), "규칙": ("📜 클랜 규칙", "{내용}"), "전쟁": ("⚔️ 클랜전 소집", "{내용}"),
              "훈련": ("🏋️ 합동 훈련", "{내용}"), "휴식": ("😴 휴식 공지", "{내용}"), "업데이트": ("🆕 업데이트", "{내용}")}
WELCOME_TPL = ["{user}님 환영합니다! 🎉", "⚔️ {user} 전사가 합류했습니다!", "{server}에 {user}님이 입장! 패널에서 help를 눌러보세요", "새 클랜원 {user} 등장 👋",
               "{user}님, 티밍은 🚨 버튼!", "🌟 {user}님 어서오세요!", "{user} 님 가입을 환영합니다. 신청은 패널 → 클랜 → 가입 신청", "환영해요 {user}! 오늘도 즐겜 🎮"]

# ───────────────────────────── DB ─────────────────────────────
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
db.executescript("""
CREATE TABLE IF NOT EXISTS config(guild INTEGER PRIMARY KEY, admin_role INTEGER, log_ch INTEGER, welcome_ch INTEGER, teaming_role INTEGER,
  invite TEXT, automod_badword INTEGER DEFAULT 0, automod_link INTEGER DEFAULT 0, automod_spam INTEGER DEFAULT 0, welcome_msg TEXT,
  board_ch INTEGER, board_msg INTEGER, board_title TEXT, board_n INTEGER DEFAULT 10, board_sort TEXT DEFAULT 'power', board_auto INTEGER DEFAULT 1,
  clan_name TEXT, clan_desc TEXT, clan_rules TEXT, win_pts INTEGER DEFAULT 100, loss_pts INTEGER DEFAULT 50);
CREATE TABLE IF NOT EXISTS warns(id INTEGER PRIMARY KEY AUTOINCREMENT, guild INTEGER, user INTEGER, mod INTEGER, reason TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS members(guild INTEGER, user INTEGER, roblox TEXT, main TEXT, power INTEGER DEFAULT 0, wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
  joined INTEGER, title TEXT, memo TEXT, position TEXT, activity INTEGER DEFAULT 0, mvp INTEGER DEFAULT 0, attend INTEGER DEFAULT 0, intro TEXT, PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS points(guild INTEGER, user INTEGER, pts INTEGER DEFAULT 0, last_daily INTEGER DEFAULT 0, streak INTEGER DEFAULT 0, PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS badwords(guild INTEGER, word TEXT, PRIMARY KEY(guild,word));
CREATE TABLE IF NOT EXISTS titles(guild INTEGER, name TEXT, PRIMARY KEY(guild,name));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, guild INTEGER, name TEXT, desc TEXT, open INTEGER DEFAULT 1, winner INTEGER, ts INTEGER);
CREATE TABLE IF NOT EXISTS event_join(event INTEGER, user INTEGER, PRIMARY KEY(event,user));
CREATE TABLE IF NOT EXISTS squads(guild INTEGER, name TEXT, leader INTEGER, PRIMARY KEY(guild,name));
CREATE TABLE IF NOT EXISTS squad_mem(guild INTEGER, name TEXT, user INTEGER, PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS inventory(guild INTEGER, user INTEGER, item TEXT, qty INTEGER DEFAULT 0, PRIMARY KEY(guild,user,item));
CREATE TABLE IF NOT EXISTS applications(guild INTEGER, user INTEGER, roblox TEXT, main TEXT, ts INTEGER, PRIMARY KEY(guild,user));
CREATE TABLE IF NOT EXISTS tier_roles(guild INTEGER, tier TEXT, role INTEGER, PRIMARY KEY(guild,tier));
CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY AUTOINCREMENT, guild INTEGER, winner INTEGER, loser INTEGER, note TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS notes(guild INTEGER, user INTEGER, idx INTEGER, text TEXT);
""")
db.commit()

def q1(sql, *a): return db.execute(sql, a).fetchone()
def qa(sql, *a): return db.execute(sql, a).fetchall()
def ex(sql, *a): db.execute(sql, a); db.commit()

def cfg(gid):
    ex("INSERT OR IGNORE INTO config(guild) VALUES(?)", gid)
    return q1("SELECT * FROM config WHERE guild=?", gid)

def set_cfg(gid, key, val): cfg(gid); ex(f"UPDATE config SET {key}=? WHERE guild=?", val, gid)

def mrow(gid, uid):
    ex("INSERT OR IGNORE INTO members(guild,user,joined) VALUES(?,?,?)", gid, uid, int(time.time()))
    return q1("SELECT * FROM members WHERE guild=? AND user=?", gid, uid)

def mset(gid, uid, key, val): mrow(gid, uid); ex(f"UPDATE members SET {key}=? WHERE guild=? AND user=?", val, gid, uid)

def prow(gid, uid):
    ex("INSERT OR IGNORE INTO points(guild,user) VALUES(?,?)", gid, uid)
    return q1("SELECT * FROM points WHERE guild=? AND user=?", gid, uid)

def add_pts(gid, uid, n):
    prow(gid, uid); ex("UPDATE points SET pts=MAX(0,pts+?) WHERE guild=? AND user=?", n, gid, uid)
    return prow(gid, uid)["pts"]

def tier_of(p):
    t = TIERS[0]
    for row in TIERS:
        if p >= row[0]: t = row
    return t

def next_tier(p): return next((x for x in TIERS if x[0] > p), None)

# ───────────────────────────── 봇 / 공용 ─────────────────────────────
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class ClanBot(commands.Bot):
    async def setup_hook(self):
        self.add_view(PanelView())

bot = ClanBot(command_prefix="!", intents=intents)
tree = bot.tree

def emb(title, desc="", color=0x5865F2):
    e = discord.Embed(title=title, description=desc, color=color)
    e.timestamp = datetime.datetime.now(datetime.timezone.utc)
    return e

def is_admin(inter) -> bool:
    m = inter.user
    if not isinstance(m, discord.Member): return False
    if m.guild_permissions.manage_guild or m.guild_permissions.administrator: return True
    role = cfg(inter.guild_id)["admin_role"]
    return role is not None and any(r.id == role for r in m.roles)

async def log(guild, embed):
    ch_id = cfg(guild.id)["log_ch"]
    if ch_id and (ch := guild.get_channel(ch_id)):
        try: await ch.send(embed=embed)
        except discord.HTTPException: pass

async def reply(inter, out, view=None):
    """모든 응답은 비공개(ephemeral)"""
    kw = dict(ephemeral=True)
    if view is not None: kw["view"] = view
    if isinstance(out, discord.Embed): kw["embed"] = out
    elif isinstance(out, tuple):
        kw["content"] = out[0]
        if len(out) > 1 and out[1] is not None: kw["embed"] = out[1]
    else: kw["content"] = str(out)[:1990]
    if inter.response.is_done(): await inter.followup.send(**kw)
    else: await inter.response.send_message(**kw)

class FeatErr(Exception): pass

def name_of(guild, uid):
    m = guild.get_member(uid)
    return m.display_name if m else f"<@{uid}>"

def fmt_member(guild, r):
    t = tier_of(r["power"])
    return f"{name_of(guild, r['user'])} — {r['power']:,} {t[2]}"

# ═══════════════════════════ 기능 레지스트리 ═══════════════════════════
class P:
    """기능 파라미터: kind = str | int | float | member | role | channel | list | choice"""
    def __init__(self, name, label, kind="str", required=True, ph="", lo=None, hi=None, choices=None):
        self.name, self.label, self.kind, self.required, self.ph, self.lo, self.hi, self.choices = name, label, kind, required, ph, lo, hi, choices

class Feature:
    __slots__ = ("id", "name", "cat", "desc", "admin", "params", "fn", "keys")
    def __init__(self, fid, name, cat, desc, admin, params, fn, keys):
        self.id, self.name, self.cat, self.desc, self.admin, self.params, self.fn, self.keys = fid, name, cat, desc, admin, params, fn, keys

FEATURES: dict = {}
CATS: dict = {}
_seq = [0]

def add_feat(cat, name, desc, fn, params=(), admin=False, keys=""):
    _seq[0] += 1
    f = Feature(f"{_seq[0]:04d}", name, cat, desc, bool(admin), list(params), fn, keys)
    FEATURES[f.id] = f
    CATS.setdefault(cat, []).append(f)
    return f

def feat(cat, name, desc, params=(), admin=False, keys=""):
    def deco(fn):
        add_feat(cat, name, desc, fn, params, admin, keys); return fn
    return deco

def search(query, admin_ok, limit=25):
    q = query.strip().lower()
    toks = [t for t in re.split(r"[\s,/]+", q) if t]
    scored = []
    for f in FEATURES.values():
        if f.admin and not admin_ok: continue
        hay = f"{f.id} {f.name} {f.cat} {f.desc} {f.keys}".lower()
        if q == f.id: scored.append((100, f)); continue
        s = 0
        if q and q in f.name.lower(): s += 50
        if q and q in f.cat.lower(): s += 20
        for t in toks:
            if t in f.name.lower(): s += 10
            elif t in hay: s += 3
        if s: scored.append((s, f))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    return [f for _, f in scored[:limit]]

# ── 파라미터 파싱 ──
def parse_member(inter, s):
    s = s.strip()
    if not s: raise FeatErr("멤버를 입력하세요.")
    m = re.match(r"<@!?(\d+)>", s)
    uid = int(m.group(1)) if m else (int(s) if s.isdigit() else None)
    if uid:
        mem = inter.guild.get_member(uid)
        if mem: return mem
    sl = s.lower().lstrip("@")
    for mem in inter.guild.members:
        if mem.name.lower() == sl or mem.display_name.lower() == sl or (mem.global_name or "").lower() == sl: return mem
    for mem in inter.guild.members:
        if sl in mem.display_name.lower() or sl in mem.name.lower(): return mem
    raise FeatErr(f"멤버 `{s}` 를 찾을 수 없어요. (멘션, ID, 닉네임 가능)")

def parse_role(inter, s):
    s = s.strip(); m = re.match(r"<@&(\d+)>", s)
    rid = int(m.group(1)) if m else (int(s) if s.isdigit() else None)
    if rid and (r := inter.guild.get_role(rid)): return r
    for r in inter.guild.roles:
        if r.name.lower() == s.lower().lstrip("@"): return r
    for r in inter.guild.roles:
        if s.lower() in r.name.lower(): return r
    raise FeatErr(f"역할 `{s}` 를 찾을 수 없어요.")

def parse_channel(inter, s):
    s = s.strip(); m = re.match(r"<#(\d+)>", s)
    cid = int(m.group(1)) if m else (int(s) if s.isdigit() else None)
    if cid and (c := inter.guild.get_channel(cid)): return c
    for c in inter.guild.channels:
        if c.name.lower() == s.lower().lstrip("#"): return c
    for c in inter.guild.channels:
        if s.lower() in c.name.lower(): return c
    raise FeatErr(f"채널 `{s}` 를 찾을 수 없어요.")

def parse_value(inter, p: P, raw: str):
    raw = (raw or "").strip()
    if not raw:
        if p.required: raise FeatErr(f"`{p.label}` 은(는) 필수예요.")
        return None
    if p.kind == "int":
        try: v = int(raw.replace(",", ""))
        except ValueError: raise FeatErr(f"`{p.label}` 은(는) 정수여야 해요.")
    elif p.kind == "float":
        try: v = float(raw.replace(",", ""))
        except ValueError: raise FeatErr(f"`{p.label}` 은(는) 숫자여야 해요.")
    elif p.kind == "member": return parse_member(inter, raw)
    elif p.kind == "role": return parse_role(inter, raw)
    elif p.kind == "channel": return parse_channel(inter, raw)
    elif p.kind == "list": return [x.strip() for x in raw.split(",") if x.strip()]
    elif p.kind == "choice":
        if raw not in p.choices: raise FeatErr(f"`{p.label}` 은(는) {', '.join(p.choices)} 중 하나여야 해요.")
        return raw
    else: return raw
    if p.lo is not None and v < p.lo: raise FeatErr(f"`{p.label}` 최소값은 {p.lo}")
    if p.hi is not None and v > p.hi: raise FeatErr(f"`{p.label}` 최대값은 {p.hi}")
    return v

async def execute(inter, f: Feature, args: dict):
    if f.admin and not is_admin(inter):
        return await reply(inter, "⛔ 이 기능은 **관리자 역할**만 사용할 수 있어요.")
    try:
        out = await f.fn(inter, args)
    except FeatErr as e:
        out = f"❌ {e}"
    except discord.Forbidden:
        out = "❌ 봇 권한이 부족해요. (봇 역할을 더 위로 올려주세요)"
    except discord.HTTPException as e:
        out = f"❌ 디스코드 오류: {e.text[:200] if hasattr(e, 'text') else e}"
    if out is None: out = "✅ 완료"
    await reply(inter, out)
    if f.admin:
        e = emb(f"🛠️ 관리 기능 실행: {f.name}", f"실행자: {inter.user.mention}\n입력: " + ", ".join(f"{k}={getattr(v, 'mention', v)}" for k, v in args.items())[:800], 0x95A5A6)
        await log(inter.guild, e)

class FeatureModal(discord.ui.Modal):
    def __init__(self, f: Feature):
        super().__init__(title=f"[{f.id}] {f.name}"[:45])
        self.f = f; self.inputs = []
        for p in f.params[:5]:
            ti = discord.ui.TextInput(label=p.label[:45], required=p.required, placeholder=(p.ph or {"member": "@멘션 / ID / 닉네임", "role": "역할 이름 또는 @역할", "channel": "#채널", "int": "숫자", "list": "쉼표로 구분"}.get(p.kind, ""))[:100],
                                      max_length=1000 if p.kind == "str" else 200, style=discord.TextStyle.paragraph if p.kind == "str" and "내용" in p.label else discord.TextStyle.short)
            self.add_item(ti); self.inputs.append((p, ti))
    async def on_submit(self, inter: discord.Interaction):
        args = {}
        try:
            for p, ti in self.inputs: args[p.name] = parse_value(inter, p, ti.value)
        except FeatErr as e:
            return await reply(inter, f"❌ {e}")
        await execute(inter, self.f, args)

async def run_feature(inter, f: Feature):
    if f.admin and not is_admin(inter):
        return await reply(inter, "⛔ 이 기능은 **관리자 역할**만 사용할 수 있어요.")
    if f.params: await inter.response.send_modal(FeatureModal(f))
    else: await execute(inter, f, {})

# ═══════════════════════════ 패널 UI ═══════════════════════════
def feature_line(f): return f"`{f.id}` {'🔒 ' if f.admin else ''}**{f.name}** — {f.desc[:60]}"

class FeatureSelect(discord.ui.Select):
    def __init__(self, feats, placeholder="실행할 기능 선택"):
        opts = [discord.SelectOption(label=f"{f.name}"[:100], value=f.id, description=f.desc[:100], emoji="🔒" if f.admin else "▶️") for f in feats[:25]]
        super().__init__(placeholder=placeholder, options=opts or [discord.SelectOption(label="결과 없음", value="none")])
    async def callback(self, inter):
        f = FEATURES.get(self.values[0])
        if not f: return await reply(inter, "결과가 없어요.")
        await run_feature(inter, f)

class ResultsView(discord.ui.View):
    def __init__(self, feats):
        super().__init__(timeout=600); self.add_item(FeatureSelect(feats))

class SearchModal(discord.ui.Modal, title="🔍 기능 검색"):
    query = discord.ui.TextInput(label="찾고 싶은 기능 (단어, 번호, 카테고리)", placeholder="예: 전투력, 밴, 운세, 사이타마, 0012", max_length=100)
    async def on_submit(self, inter):
        feats = search(self.query.value, is_admin(inter))
        if not feats: return await reply(inter, f"🔍 `{self.query.value}` 검색 결과가 없어요.")
        e = emb(f"🔍 '{self.query.value}' 검색 결과 {len(feats)}개", "\n".join(feature_line(f) for f in feats), 0x1ABC9C)
        e.set_footer(text="아래 메뉴에서 선택하면 실행돼요 · 결과는 본인만 보여요")
        await reply(inter, e, ResultsView(feats))

class RunModal(discord.ui.Modal, title="▶️ 기능 번호로 실행"):
    fid = discord.ui.TextInput(label="기능 번호 (예: 0012)", max_length=6)
    async def on_submit(self, inter):
        f = FEATURES.get(self.fid.value.strip().zfill(4))
        if not f: return await reply(inter, "그 번호의 기능이 없어요.")
        await run_feature(inter, f)

class FeatureListView(discord.ui.View):
    """카테고리 내 기능 목록 (25개씩 페이지)"""
    def __init__(self, cat, admin_ok, page=0):
        super().__init__(timeout=600)
        self.cat, self.admin_ok, self.page = cat, admin_ok, page
        self.feats = [f for f in CATS[cat] if admin_ok or not f.admin]
        self.pages = max(1, (len(self.feats) + 24) // 25)
        self.add_item(FeatureSelect(self.feats[page * 25:(page + 1) * 25], f"{cat} 기능 선택 ({page + 1}/{self.pages})"))
    def embed(self):
        chunk = self.feats[self.page * 25:(self.page + 1) * 25]
        e = emb(f"📂 {self.cat} ({len(self.feats)}개)", "\n".join(feature_line(f) for f in chunk) or "없음", 0x3498DB)
        e.set_footer(text=f"페이지 {self.page + 1}/{self.pages}")
        return e
    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=1)
    async def prev(self, inter, _):
        v = FeatureListView(self.cat, self.admin_ok, (self.page - 1) % self.pages)
        await inter.response.edit_message(embed=v.embed(), view=v)
    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=1)
    async def nxt(self, inter, _):
        v = FeatureListView(self.cat, self.admin_ok, (self.page + 1) % self.pages)
        await inter.response.edit_message(embed=v.embed(), view=v)

class CategorySelect(discord.ui.Select):
    def __init__(self, admin_ok, cats):
        opts = [discord.SelectOption(label=c[:100], value=c, description=f"{sum(1 for f in CATS[c] if admin_ok or not f.admin)}개 기능") for c in cats[:25]]
        super().__init__(placeholder="카테고리 선택", options=opts)
        self.admin_ok = admin_ok
    async def callback(self, inter):
        v = FeatureListView(self.values[0], self.admin_ok)
        await inter.response.send_message(embed=v.embed(), view=v, ephemeral=True)

class CategoryView(discord.ui.View):
    def __init__(self, admin_ok):
        super().__init__(timeout=600)
        cats = [c for c in CATS if any(admin_ok or not f.admin for f in CATS[c])]
        for i in range(0, len(cats), 25):
            self.add_item(CategorySelect(admin_ok, cats[i:i + 25]))

def help_embed(inter):
    admin_ok = is_admin(inter)
    total = sum(1 for f in FEATURES.values() if admin_ok or not f.admin)
    e = emb("📖 help — 가강전 클랜봇", f"사용 가능한 기능 **{total:,}개** (전체 {len(FEATURES):,}개)\n모든 결과는 **본인에게만** 비공개로 표시돼요.", 0x1ABC9C)
    e.add_field(name="🔍 검색", value="단어·번호·카테고리로 기능을 찾고 메뉴에서 바로 실행", inline=False)
    e.add_field(name="📂 카테고리", value="카테고리별로 기능 둘러보기 (25개씩 페이지)", inline=False)
    e.add_field(name="📊 내 정보 / 🏆 랭킹 / 🚨 티밍", value="자주 쓰는 기능 바로가기", inline=False)
    lines = [f"{'🔒' if all(f.admin for f in CATS[c]) else '•'} {c} ({sum(1 for f in CATS[c] if admin_ok or not f.admin)})" for c in CATS if any(admin_ok or not f.admin for f in CATS[c])]
    half = (len(lines) + 1) // 2
    e.add_field(name="카테고리", value="\n".join(lines[:half]) or "-", inline=True)
    e.add_field(name="​", value="\n".join(lines[half:]) or "​", inline=True)
    e.add_field(name="권한", value=("✅ 관리자 역할 — 🔒 관리 기능 검색/실행 가능" if admin_ok else "일반 멤버 — 🔒 관리 기능은 보이지 않아요\n클랜 데이터(전투력·전적·칭호 등)는 관리자만 수정"), inline=False)
    e.set_footer(text="슬래시: /help /검색 /실행 /패널 /티밍")
    return e

class TeamingModal(discord.ui.Modal, title="🚨 티밍 호출"):
    link = discord.ui.TextInput(label="서버 직행 링크 (비우면 기본 링크)", required=False, max_length=300)
    note = discord.ui.TextInput(label="상황", required=False, default="티밍 당하는 중!", max_length=200)
    async def on_submit(self, inter):
        await send_teaming(inter, self.link.value or None, self.note.value or "티밍 당하는 중!")

async def send_teaming(inter, link, note):
    c = cfg(inter.guild_id)
    url = link or c["invite"] or GAME_LINK
    role = f"<@&{c['teaming_role']}>" if c["teaming_role"] else "@here"
    e = emb("🚨 긴급 호출! 티밍 발생", f"**{inter.user.display_name}** 님이 도움을 요청했어요!\n> {note}", 0xFF0000)
    e.add_field(name="🔗 서버 바로가기", value=url, inline=False)
    e.set_thumbnail(url=inter.user.display_avatar.url)
    v = discord.ui.View(); v.add_item(discord.ui.Button(label="서버 입장", url=url, emoji="⚔️"))
    await inter.channel.send(content=role, embed=e, view=v, allowed_mentions=discord.AllowedMentions(roles=True, everyone=True))
    await reply(inter, "✅ 클랜원 호출을 보냈어요!")

class PanelView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="검색", emoji="🔍", style=discord.ButtonStyle.primary, custom_id="gp:search")
    async def b_search(self, inter, _): await inter.response.send_modal(SearchModal())
    @discord.ui.button(label="help", emoji="📖", style=discord.ButtonStyle.success, custom_id="gp:help")
    async def b_help(self, inter, _): await reply(inter, help_embed(inter))
    @discord.ui.button(label="카테고리", emoji="📂", style=discord.ButtonStyle.secondary, custom_id="gp:cat")
    async def b_cat(self, inter, _): await reply(inter, "📂 카테고리를 선택하세요.", CategoryView(is_admin(inter)))
    @discord.ui.button(label="번호 실행", emoji="▶️", style=discord.ButtonStyle.secondary, custom_id="gp:run")
    async def b_run(self, inter, _): await inter.response.send_modal(RunModal())
    @discord.ui.button(label="내 정보", emoji="📊", style=discord.ButtonStyle.secondary, custom_id="gp:me", row=1)
    async def b_me(self, inter, _): await reply(inter, profile_embed(inter.guild, inter.user))
    @discord.ui.button(label="랭킹", emoji="🏆", style=discord.ButtonStyle.secondary, custom_id="gp:rank", row=1)
    async def b_rank(self, inter, _): await reply(inter, rank_embed(inter.guild, "power", "⚔️ 전투력 랭킹", 1))
    @discord.ui.button(label="출석", emoji="📅", style=discord.ButtonStyle.secondary, custom_id="gp:daily", row=1)
    async def b_daily(self, inter, _): await reply(inter, await do_daily(inter))
    @discord.ui.button(label="티밍 호출", emoji="🚨", style=discord.ButtonStyle.danger, custom_id="gp:team", row=1)
    async def b_team(self, inter, _): await inter.response.send_modal(TeamingModal())

def panel_embed(guild):
    c = cfg(guild.id)
    e = emb(f"⚔️ {c['clan_name'] or guild.name} 클랜 패널", "버튼을 눌러 기능을 사용하세요. 모든 응답은 **본인에게만** 보여요.", 0xE91E63)
    e.add_field(name="🔍 검색", value="원하는 기능 찾기")
    e.add_field(name="📖 help", value="도움말 · 카테고리 목록")
    e.add_field(name="📂 카테고리", value="기능 둘러보기")
    e.add_field(name="▶️ 번호 실행", value="기능 번호로 바로 실행")
    e.add_field(name="📊 내 정보 · 🏆 랭킹 · 📅 출석", value="바로가기")
    e.add_field(name="🚨 티밍 호출", value="클랜원 소집")
    e.set_footer(text=f"기능 {len(FEATURES):,}개 탑재")
    return e

# ── 공용 임베드 ──
def profile_embed(guild, m):
    r = mrow(guild.id, m.id); p = prow(guild.id, m.id)
    rank = q1("SELECT COUNT(*)+1 c FROM members WHERE guild=? AND power>?", guild.id, r["power"])["c"]
    t = tier_of(r["power"]); nt = next_tier(r["power"])
    games = r["wins"] + r["losses"]
    e = emb(f"📊 {m.display_name}", color=0x9B59B6); e.set_thumbnail(url=m.display_avatar.url)
    e.add_field(name="순위", value=f"#{rank}"); e.add_field(name="전투력", value=f"{r['power']:,}"); e.add_field(name="티어", value=f"{t[2]} {t[1]}")
    e.add_field(name="전적", value=f"{r['wins']}승 {r['losses']}패 ({(r['wins'] * 100 // games) if games else 0}%)")
    e.add_field(name="포인트", value=f"{p['pts']:,}P"); e.add_field(name="출석", value=f"{r['attend']}일 (연속 {p['streak']})")
    e.add_field(name="로블록스", value=r["roblox"] or "미등록"); e.add_field(name="주캐", value=r["main"] or "미설정"); e.add_field(name="직책", value=r["position"] or "-")
    e.add_field(name="칭호", value=r["title"] or "-"); e.add_field(name="MVP", value=str(r["mvp"])); e.add_field(name="활동점수", value=str(r["activity"]))
    if r["intro"]: e.add_field(name="소개", value=r["intro"], inline=False)
    if nt: e.set_footer(text=f"다음 티어 {nt[1]}까지 {nt[0] - r['power']:,}")
    return e

RANK_KEYS = {"power": "전투력", "wins": "승리", "losses": "패배", "activity": "활동점수", "mvp": "MVP", "attend": "출석"}
def rank_embed(guild, key, title, page=1, per=10, where=""):
    rows = qa(f"SELECT * FROM members WHERE guild=? {where} ORDER BY {key} DESC, power DESC", guild.id)
    rows = [r for r in rows if r[key] > 0]
    e = emb(title, color=0xF1C40F)
    if not rows: e.description = "아직 기록이 없어요."; return e
    start = (page - 1) * per; lines = []
    for i, r in enumerate(rows[start:start + per], start=start + 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"`{i:>2}.`")
        extra = f"{r[key]:,}" if key != "power" else ""
        lines.append(f"{medal} **{name_of(guild, r['user'])}** — {r['power']:,} {tier_of(r['power'])[2]} {('· ' + RANK_KEYS[key] + ' ' + extra) if extra else ''}")
    e.description = "\n".join(lines)
    e.set_footer(text=f"페이지 {page}/{max(1, (len(rows) + per - 1) // per)} · 총 {len(rows)}명")
    return e

async def refresh_board(guild):
    """관리자가 설정한 랭킹표 게시판 자동 갱신"""
    c = cfg(guild.id)
    if not c["board_ch"]: return
    ch = guild.get_channel(c["board_ch"])
    if not ch: return
    e = rank_embed(guild, c["board_sort"] or "power", c["board_title"] or "🏆 클랜 랭킹표", 1, c["board_n"] or 10)
    e.set_footer(text=f"마지막 갱신 · 정렬: {RANK_KEYS.get(c['board_sort'] or 'power')}")
    try:
        if c["board_msg"]:
            msg = await ch.fetch_message(c["board_msg"]); await msg.edit(embed=e); return
    except discord.HTTPException: pass
    msg = await ch.send(embed=e); set_cfg(guild.id, "board_msg", msg.id)

async def do_daily(inter):
    g, u = inter.guild_id, inter.user.id
    p = prow(g, u); today = datetime.date.today().toordinal()
    if p["last_daily"] == today: return "오늘은 이미 출석했어요! 내일 또 봐요 👋"
    streak = p["streak"] + 1 if p["last_daily"] == today - 1 else 1
    bonus = min(streak, 7) * 10
    ex("UPDATE points SET last_daily=?, streak=? WHERE guild=? AND user=?", today, streak, g, u)
    r = mrow(g, u); mset(g, u, "attend", r["attend"] + 1)
    total = add_pts(g, u, 100 + bonus)
    return f"✅ 출석 완료! +{100 + bonus}P (연속 {streak}일 보너스 {bonus}) · 보유 {total:,}P"

async def change_power(inter, m, new, how):
    old = mrow(inter.guild_id, m.id)["power"]; new = max(0, new)
    mset(inter.guild_id, m.id, "power", new)
    to, tn = tier_of(old), tier_of(new)
    msg = f"{m.mention} 전투력 {how}\n`{old:,}` → **`{new:,}`** {tn[2]} {tn[1]}"
    if to != tn:
        msg += f"\n🎉 티어 변동: {to[1]} → **{tn[1]}**"
        await apply_tier_role(inter.guild, m, tn[1])
    e = emb("⚔️ 전투력 변경", msg, 0x9B59B6); e.set_footer(text=f"처리: {inter.user.display_name}")
    await log(inter.guild, e)
    if cfg(inter.guild_id)["board_auto"]: asyncio.create_task(refresh_board(inter.guild))
    return e

async def apply_tier_role(guild, m, tier_name):
    rows = {r["tier"]: r["role"] for r in qa("SELECT * FROM tier_roles WHERE guild=?", guild.id)}
    if not rows: return
    try:
        rm = [guild.get_role(rid) for t, rid in rows.items() if t != tier_name and guild.get_role(rid) in m.roles]
        if rm: await m.remove_roles(*rm)
        if (rid := rows.get(tier_name)) and (role := guild.get_role(rid)): await m.add_roles(role)
    except discord.Forbidden: pass

# ═══════════════════════════ 기능 정의 ═══════════════════════════
A = True  # admin 표시용
PM = P("m", "멤버", "member")

# ───────── 🔒 설정 ─────────
@feat("🔒 설정", "관리자 역할 지정", "관리 기능·클랜 데이터 수정 권한 역할", [P("r", "역할", "role")], A, "admin role 권한")
async def _(i, a): set_cfg(i.guild_id, "admin_role", a["r"].id); return f"✅ 관리자 역할 → {a['r'].mention}"
@feat("🔒 설정", "로그 채널 지정", "관리 로그를 보낼 채널", [P("c", "채널", "channel")], A, "log")
async def _(i, a): set_cfg(i.guild_id, "log_ch", a["c"].id); return f"✅ 로그 채널 → {a['c'].mention}"
@feat("🔒 설정", "환영 채널 지정", "새 멤버 환영 메시지 채널", [P("c", "채널", "channel")], A, "welcome")
async def _(i, a): set_cfg(i.guild_id, "welcome_ch", a["c"].id); return f"✅ 환영 채널 → {a['c'].mention}"
@feat("🔒 설정", "환영 메시지 직접 입력", "{user} {server} 사용 가능", [P("t", "내용", "str")], A)
async def _(i, a): set_cfg(i.guild_id, "welcome_msg", a["t"]); return "✅ 환영 메시지 저장"
@feat("🔒 설정", "티밍 호출 역할 지정", "🚨 티밍 호출 시 멘션할 역할", [P("r", "역할", "role")], A, "teaming")
async def _(i, a): set_cfg(i.guild_id, "teaming_role", a["r"].id); return f"✅ 티밍 역할 → {a['r'].mention}"
@feat("🔒 설정", "기본 서버 링크 지정", "티밍 호출에 붙는 기본 직행 링크", [P("u", "링크")], A, "invite")
async def _(i, a): set_cfg(i.guild_id, "invite", a["u"]); return "✅ 기본 링크 저장"
@feat("🔒 설정", "클랜 이름 설정", "패널/랭킹표에 표시될 클랜 이름", [P("t", "클랜 이름")], A)
async def _(i, a): set_cfg(i.guild_id, "clan_name", a["t"]); return f"✅ 클랜 이름 → {a['t']}"
@feat("🔒 설정", "클랜 소개 설정", "클랜 소개문", [P("t", "내용", "str")], A)
async def _(i, a): set_cfg(i.guild_id, "clan_desc", a["t"]); return "✅ 클랜 소개 저장"
@feat("🔒 설정", "클랜 규칙 설정", "클랜 규칙문", [P("t", "내용", "str")], A)
async def _(i, a): set_cfg(i.guild_id, "clan_rules", a["t"]); return "✅ 클랜 규칙 저장"
@feat("🔒 설정", "승리 전투력 설정", "승리 1회당 오르는 전투력", [P("n", "값", "int", lo=0, hi=100000)], A)
async def _(i, a): set_cfg(i.guild_id, "win_pts", a["n"]); return f"✅ 승리당 +{a['n']}"
@feat("🔒 설정", "패배 전투력 설정", "패배 1회당 내려가는 전투력", [P("n", "값", "int", lo=0, hi=100000)], A)
async def _(i, a): set_cfg(i.guild_id, "loss_pts", a["n"]); return f"✅ 패배당 -{a['n']}"
@feat("🔒 설정", "설정 보기", "현재 서버 설정 전체", [], A)
async def _(i, a):
    c = cfg(i.guild_id); r = lambda x: f"<@&{x}>" if x else "미설정"; ch = lambda x: f"<#{x}>" if x else "미설정"
    e = emb("⚙️ 서버 설정")
    for k, v in [("관리자 역할", r(c["admin_role"])), ("티밍 역할", r(c["teaming_role"])), ("로그 채널", ch(c["log_ch"])), ("환영 채널", ch(c["welcome_ch"])),
                 ("랭킹표 채널", ch(c["board_ch"])), ("승/패 전투력", f"+{c['win_pts']} / -{c['loss_pts']}"), ("클랜 이름", c["clan_name"] or "-"),
                 ("자동관리", f"금지어 {'ON' if c['automod_badword'] else 'OFF'} · 링크 {'ON' if c['automod_link'] else 'OFF'} · 도배 {'ON' if c['automod_spam'] else 'OFF'}")]:
        e.add_field(name=k, value=v)
    return e
for _k, _label in [("automod_badword", "금지어 차단"), ("automod_link", "링크 차단"), ("automod_spam", "도배 차단"), ("board_auto", "랭킹표 자동 갱신")]:
    for _on in (1, 0):
        def _mk(k=_k, on=_on, label=_label):
            async def fn(i, a): set_cfg(i.guild_id, k, on); return f"✅ {label}: {'ON' if on else 'OFF'}"
            return fn
        add_feat("🔒 설정", f"{_label} {'켜기' if _on else '끄기'}", f"{_label} 자동 기능 {'활성화' if _on else '비활성화'}", _mk(), [], A, "automod 자동")
@feat("🔒 설정", "금지어 추가", "자동 삭제할 단어 추가", [P("w", "단어")], A)
async def _(i, a): ex("INSERT OR IGNORE INTO badwords VALUES(?,?)", i.guild_id, a["w"]); return f"✅ 금지어 추가: `{a['w']}`"
@feat("🔒 설정", "금지어 삭제", "금지어 제거", [P("w", "단어")], A)
async def _(i, a): ex("DELETE FROM badwords WHERE guild=? AND word=?", i.guild_id, a["w"]); return f"✅ 금지어 삭제: `{a['w']}`"
@feat("🔒 설정", "금지어 목록", "등록된 금지어", [], A)
async def _(i, a): return "📃 " + (", ".join(r["word"] for r in qa("SELECT word FROM badwords WHERE guild=?", i.guild_id)) or "없음")
@feat("🔒 설정", "금지어 전체 삭제", "금지어 초기화", [], A)
async def _(i, a): ex("DELETE FROM badwords WHERE guild=?", i.guild_id); return "✅ 금지어 초기화"
for _n, _t in enumerate(WELCOME_TPL, 1):
    def _mk(t=_t):
        async def fn(i, a): set_cfg(i.guild_id, "welcome_msg", t); return f"✅ 환영 메시지 → {t}"
        return fn
    add_feat("🔒 설정", f"환영 템플릿 {_n}", _t, _mk(), [], A, "welcome 환영")
for _t in TIERS:
    def _mk(tn=_t[1]):
        async def fn(i, a): ex("INSERT OR REPLACE INTO tier_roles VALUES(?,?,?)", i.guild_id, tn, a["r"].id); return f"✅ {tn} 티어 ↔ {a['r'].mention} 연결"
        return fn
    add_feat("🔒 설정", f"{_t[1]} 티어 역할 연결", f"전투력 {_t[0]:,}+ 티어 달성 시 자동 지급될 역할", _mk(), [P("r", "역할", "role")], A, "tier role")
@feat("🔒 설정", "티어 역할 연결 해제", "모든 티어 역할 연결 삭제", [], A)
async def _(i, a): ex("DELETE FROM tier_roles WHERE guild=?", i.guild_id); return "✅ 티어 역할 연결 해제"
@feat("🔒 설정", "티어 역할 전원 재적용", "모든 클랜원 티어 역할 재지급", [], A)
async def _(i, a):
    n = 0
    for r in qa("SELECT * FROM members WHERE guild=?", i.guild_id):
        if (m := i.guild.get_member(r["user"])): await apply_tier_role(i.guild, m, tier_of(r["power"])[1]); n += 1
    return f"✅ {n}명 티어 역할 재적용"
@feat("🔒 설정", "패널 설치", "현재 채널에 버튼 패널 설치", [], A, "panel 버튼")
async def _(i, a): await i.channel.send(embed=panel_embed(i.guild), view=PanelView()); return "✅ 패널 설치 완료"
@feat("🔒 설정", "패널 설치 (채널 지정)", "지정 채널에 버튼 패널 설치", [P("c", "채널", "channel")], A, "panel")
async def _(i, a): await a["c"].send(embed=panel_embed(i.guild), view=PanelView()); return f"✅ {a['c'].mention} 에 패널 설치"

# ───────── 🔒 관리 ─────────
@feat("🔒 관리", "추방", "멤버 추방", [PM, P("why", "사유", required=False)], A, "kick")
async def _(i, a): await a["m"].kick(reason=a["why"] or "사유 없음"); return f"👢 {a['m']} 추방 완료"
@feat("🔒 관리", "밴", "멤버 차단", [PM, P("why", "사유", required=False), P("d", "메시지 삭제 일수(0-7)", "int", False, lo=0, hi=7)], A, "ban")
async def _(i, a): await a["m"].ban(reason=a["why"] or "사유 없음", delete_message_days=a["d"] or 0); return f"🔨 {a['m']} 밴 완료"
@feat("🔒 관리", "밴 해제", "유저 ID로 차단 해제", [P("id", "유저 ID")], A, "unban")
async def _(i, a):
    try: u = await bot.fetch_user(int(a["id"])); await i.guild.unban(u)
    except Exception: raise FeatErr("해제 실패 (ID 확인)")
    return f"🔓 {u} 밴 해제"
@feat("🔒 관리", "밴 목록", "차단된 유저 목록", [], A)
async def _(i, a):
    bans = [b async for b in i.guild.bans(limit=30)]
    return emb(f"🔨 밴 목록 ({len(bans)})", "\n".join(f"{b.user} — {b.reason or '-'}" for b in bans) or "없음")
@feat("🔒 관리", "타임아웃", "멤버 타임아웃 (분)", [PM, P("n", "분", "int", lo=1, hi=40320), P("why", "사유", required=False)], A, "timeout mute 뮤트")
async def _(i, a): await a["m"].timeout(datetime.timedelta(minutes=a["n"]), reason=a["why"] or "사유 없음"); return f"🔇 {a['m'].mention} {a['n']}분 타임아웃"
@feat("🔒 관리", "타임아웃 해제", "타임아웃 풀기", [PM], A, "unmute")
async def _(i, a): await a["m"].timeout(None); return f"🔊 {a['m'].mention} 타임아웃 해제"
for _mins, _lab in [(1, "1분"), (5, "5분"), (10, "10분"), (30, "30분"), (60, "1시간"), (360, "6시간"), (1440, "1일"), (10080, "1주")]:
    def _mk(n=_mins, lab=_lab):
        async def fn(i, a): await a["m"].timeout(datetime.timedelta(minutes=n), reason=a["why"] or "사유 없음"); return f"🔇 {a['m'].mention} {lab} 타임아웃"
        return fn
    add_feat("🔒 관리", f"타임아웃 {_lab}", f"멤버를 {_lab} 타임아웃", _mk(), [PM, P("why", "사유", required=False)], A, "timeout 뮤트")
@feat("🔒 관리", "청소", "메시지 삭제 (1~100)", [P("n", "개수", "int", lo=1, hi=100), P("m", "특정 멤버만", "member", False)], A, "purge clear 삭제")
async def _(i, a):
    await i.response.defer(ephemeral=True)
    d = await i.channel.purge(limit=a["n"], check=(lambda x: x.author == a["m"]) if a["m"] else None)
    return f"🧹 {len(d)}개 삭제"
for _n in (5, 10, 20, 50, 100):
    def _mk(n=_n):
        async def fn(i, a): await i.response.defer(ephemeral=True); d = await i.channel.purge(limit=n); return f"🧹 {len(d)}개 삭제"
        return fn
    add_feat("🔒 관리", f"청소 {_n}개", f"최근 메시지 {_n}개 삭제", _mk(), [], A, "purge")
@feat("🔒 관리", "봇 메시지 청소", "최근 100개 중 봇 메시지 삭제", [], A)
async def _(i, a): await i.response.defer(ephemeral=True); d = await i.channel.purge(limit=100, check=lambda x: x.author.bot); return f"🧹 봇 메시지 {len(d)}개 삭제"
@feat("🔒 관리", "링크 메시지 청소", "최근 100개 중 링크 포함 메시지 삭제", [], A)
async def _(i, a): await i.response.defer(ephemeral=True); d = await i.channel.purge(limit=100, check=lambda x: "http" in x.content); return f"🧹 {len(d)}개 삭제"
@feat("🔒 관리", "첨부파일 메시지 청소", "최근 100개 중 첨부 메시지 삭제", [], A)
async def _(i, a): await i.response.defer(ephemeral=True); d = await i.channel.purge(limit=100, check=lambda x: bool(x.attachments)); return f"🧹 {len(d)}개 삭제"
@feat("🔒 관리", "슬로우모드", "채널 슬로우모드 (초, 0=해제)", [P("n", "초", "int", lo=0, hi=21600)], A, "slowmode")
async def _(i, a): await i.channel.edit(slowmode_delay=a["n"]); return f"🐢 슬로우모드 {a['n']}초"
for _s in (0, 5, 10, 30, 60, 300, 3600):
    def _mk(s=_s):
        async def fn(i, a): await i.channel.edit(slowmode_delay=s); return f"🐢 슬로우모드 {s}초" if s else "🐇 슬로우모드 해제"
        return fn
    add_feat("🔒 관리", f"슬로우모드 {_s}초" if _s else "슬로우모드 해제", "현재 채널 슬로우모드 프리셋", _mk(), [], A, "slowmode")
@feat("🔒 관리", "채널 잠금", "@everyone 메시지 금지", [], A, "lock")
async def _(i, a):
    ow = i.channel.overwrites_for(i.guild.default_role); ow.send_messages = False
    await i.channel.set_permissions(i.guild.default_role, overwrite=ow); return "🔒 채널 잠금"
@feat("🔒 관리", "채널 잠금 해제", "메시지 금지 해제", [], A, "unlock")
async def _(i, a):
    ow = i.channel.overwrites_for(i.guild.default_role); ow.send_messages = None
    await i.channel.set_permissions(i.guild.default_role, overwrite=ow); return "🔓 채널 잠금 해제"
@feat("🔒 관리", "서버 전체 잠금", "모든 텍스트 채널 메시지 금지", [], A, "lockdown")
async def _(i, a):
    n = 0
    for ch in i.guild.text_channels:
        ow = ch.overwrites_for(i.guild.default_role); ow.send_messages = False
        try: await ch.set_permissions(i.guild.default_role, overwrite=ow); n += 1
        except discord.Forbidden: pass
    return f"🔒 {n}개 채널 잠금"
@feat("🔒 관리", "서버 전체 잠금 해제", "모든 텍스트 채널 잠금 해제", [], A)
async def _(i, a):
    n = 0
    for ch in i.guild.text_channels:
        ow = ch.overwrites_for(i.guild.default_role); ow.send_messages = None
        try: await ch.set_permissions(i.guild.default_role, overwrite=ow); n += 1
        except discord.Forbidden: pass
    return f"🔓 {n}개 채널 해제"
@feat("🔒 관리", "닉네임 변경", "멤버 닉네임 변경/초기화", [PM, P("t", "새 닉네임 (비우면 초기화)", required=False)], A, "nick")
async def _(i, a): await a["m"].edit(nick=a["t"]); return f"✏️ {a['m'].mention} → {a['t'] or '초기화'}"
@feat("🔒 관리", "닉네임 접두사 추가", "닉 앞에 접두사 붙이기", [PM, P("t", "접두사")], A)
async def _(i, a): await a["m"].edit(nick=(a["t"] + a["m"].display_name)[:32]); return f"✏️ {a['m'].mention} 닉 변경"
@feat("🔒 관리", "역할 지급", "역할 주기", [PM, P("r", "역할", "role")], A, "role add")
async def _(i, a): await a["m"].add_roles(a["r"]); return f"✅ {a['m'].mention} ← {a['r'].mention}"
@feat("🔒 관리", "역할 회수", "역할 빼기", [PM, P("r", "역할", "role")], A, "role remove")
async def _(i, a): await a["m"].remove_roles(a["r"]); return f"✅ {a['m'].mention} ✖ {a['r'].mention}"
@feat("🔒 관리", "역할 전원 지급", "모든 멤버에게 역할 지급", [P("r", "역할", "role")], A)
async def _(i, a):
    await i.response.defer(ephemeral=True); n = 0
    for m in i.guild.members:
        if not m.bot and a["r"] not in m.roles:
            try: await m.add_roles(a["r"]); n += 1
            except discord.Forbidden: pass
    return f"✅ {n}명에게 {a['r'].mention} 지급"
@feat("🔒 관리", "역할 전원 회수", "모든 멤버에게서 역할 회수", [P("r", "역할", "role")], A)
async def _(i, a):
    await i.response.defer(ephemeral=True); n = 0
    for m in list(a["r"].members):
        try: await m.remove_roles(a["r"]); n += 1
        except discord.Forbidden: pass
    return f"✅ {n}명에게서 {a['r'].mention} 회수"
@feat("🔒 관리", "역할 생성", "새 역할 만들기", [P("t", "이름"), P("c", "색상 이름(빨강/파랑…)", required=False)], A)
async def _(i, a): r = await i.guild.create_role(name=a["t"], colour=discord.Colour(COLORS.get(a["c"] or "", 0))); return f"✅ 역할 생성 {r.mention}"
@feat("🔒 관리", "역할 삭제", "역할 삭제", [P("r", "역할", "role")], A)
async def _(i, a): n = a["r"].name; await a["r"].delete(); return f"🗑️ 역할 `{n}` 삭제"
@feat("🔒 관리", "역할 이름 변경", "역할 이름 바꾸기", [P("r", "역할", "role"), P("t", "새 이름")], A)
async def _(i, a): await a["r"].edit(name=a["t"]); return f"✏️ 역할 → {a['t']}"
@feat("🔒 관리", "역할 멘션 허용 토글", "역할 멘션 가능 여부 전환", [P("r", "역할", "role")], A)
async def _(i, a): await a["r"].edit(mentionable=not a["r"].mentionable); return f"✅ {a['r'].mention} 멘션 {'허용' if not a['r'].mentionable else '금지'}"
@feat("🔒 관리", "역할 분리 표시 토글", "멤버 목록에 따로 표시 전환", [P("r", "역할", "role")], A)
async def _(i, a): await a["r"].edit(hoist=not a["r"].hoist); return "✅ 전환 완료"
for _cn, _cv in COLORS.items():
    def _mk(cn=_cn, cv=_cv):
        async def fn(i, a): await a["r"].edit(colour=discord.Colour(cv)); return f"🎨 {a['r'].mention} 색상 → {cn}"
        return fn
    add_feat("🔒 관리", f"역할 색상 {_cn}", f"역할 색을 {_cn}으로", _mk(), [P("r", "역할", "role")], A, "color 색")
@feat("🔒 관리", "채널 생성", "텍스트 채널 생성", [P("t", "이름"), P("cat", "카테고리 이름", required=False)], A)
async def _(i, a):
    cat = discord.utils.find(lambda c: a["cat"] and a["cat"].lower() in c.name.lower(), i.guild.categories)
    ch = await i.guild.create_text_channel(a["t"], category=cat); return f"✅ {ch.mention} 생성"
@feat("🔒 관리", "음성 채널 생성", "음성 채널 생성", [P("t", "이름")], A)
async def _(i, a): ch = await i.guild.create_voice_channel(a["t"]); return f"✅ 🔊 {ch.name} 생성"
@feat("🔒 관리", "카테고리 생성", "채널 카테고리 생성", [P("t", "이름")], A)
async def _(i, a): await i.guild.create_category(a["t"]); return f"✅ 카테고리 {a['t']} 생성"
@feat("🔒 관리", "채널 삭제", "채널 삭제", [P("c", "채널", "channel")], A)
async def _(i, a): n = a["c"].name; await a["c"].delete(); return f"🗑️ #{n} 삭제"
@feat("🔒 관리", "채널 이름 변경", "채널 이름 바꾸기", [P("c", "채널", "channel"), P("t", "새 이름")], A)
async def _(i, a): await a["c"].edit(name=a["t"]); return f"✏️ 채널 → {a['t']}"
@feat("🔒 관리", "채널 주제 변경", "채널 토픽 설정", [P("t", "내용", "str")], A)
async def _(i, a): await i.channel.edit(topic=a["t"]); return "✅ 주제 변경"
@feat("🔒 관리", "채널 NSFW 토글", "연령 제한 전환", [], A)
async def _(i, a): await i.channel.edit(nsfw=not i.channel.nsfw); return "✅ 전환"
@feat("🔒 관리", "채널 복제", "현재 채널 복제", [], A)
async def _(i, a): ch = await i.channel.clone(); return f"✅ {ch.mention} 복제"
@feat("🔒 관리", "채널 숨기기", "@everyone 에게 채널 숨김", [], A)
async def _(i, a):
    ow = i.channel.overwrites_for(i.guild.default_role); ow.view_channel = False
    await i.channel.set_permissions(i.guild.default_role, overwrite=ow); return "🙈 채널 숨김"
@feat("🔒 관리", "채널 공개", "@everyone 에게 채널 보이기", [], A)
async def _(i, a):
    ow = i.channel.overwrites_for(i.guild.default_role); ow.view_channel = None
    await i.channel.set_permissions(i.guild.default_role, overwrite=ow); return "👁️ 채널 공개"
@feat("🔒 관리", "역할 전용 채널 설정", "특정 역할만 볼 수 있게", [P("r", "역할", "role")], A)
async def _(i, a):
    await i.channel.set_permissions(i.guild.default_role, view_channel=False); await i.channel.set_permissions(a["r"], view_channel=True)
    return f"✅ {a['r'].mention} 전용 채널"
@feat("🔒 관리", "스레드 생성", "현재 채널에 스레드", [P("t", "이름")], A)
async def _(i, a): await i.channel.create_thread(name=a["t"], type=discord.ChannelType.public_thread); return f"🧵 스레드 {a['t']} 생성"
@feat("🔒 관리", "메시지 고정", "메시지 ID로 고정", [P("id", "메시지 ID")], A, "pin")
async def _(i, a): m = await i.channel.fetch_message(int(a["id"])); await m.pin(); return "📌 고정 완료"
@feat("🔒 관리", "메시지 고정 해제", "메시지 ID로 고정 해제", [P("id", "메시지 ID")], A)
async def _(i, a): m = await i.channel.fetch_message(int(a["id"])); await m.unpin(); return "📌 해제 완료"
@feat("🔒 관리", "메시지 삭제 (ID)", "특정 메시지 삭제", [P("id", "메시지 ID")], A)
async def _(i, a): m = await i.channel.fetch_message(int(a["id"])); await m.delete(); return "🗑️ 삭제"
@feat("🔒 관리", "공지 보내기", "임베드 공지", [P("t", "제목"), P("b", "내용", "str"), P("c", "채널", "channel", False), P("ev", "@everyone (y/n)", required=False)], A, "announce")
async def _(i, a):
    e = emb(f"📢 {a['t']}", a["b"], 0xE91E63); e.set_footer(text=f"작성: {i.user.display_name}")
    await (a["c"] or i.channel).send(content="@everyone" if (a["ev"] or "").lower().startswith("y") else None, embed=e); return "✅ 공지 전송"
for _k, (_tt, _body) in NOTICE_TPL.items():
    def _mk(tt=_tt, body=_body):
        async def fn(i, a):
            e = emb(tt, body.replace("{내용}", a["b"]), 0xE91E63); e.set_footer(text=f"작성: {i.user.display_name}")
            await (a["c"] or i.channel).send(embed=e); return "✅ 공지 전송"
        return fn
    add_feat("🔒 관리", f"공지 템플릿: {_k}", f"'{_tt}' 양식으로 공지", _mk(), [P("b", "내용", "str"), P("c", "채널", "channel", False)], A, "announce 공지")
@feat("🔒 관리", "봇으로 말하기", "봇이 대신 메시지", [P("t", "내용", "str"), P("c", "채널", "channel", False)], A, "say")
async def _(i, a): await (a["c"] or i.channel).send(a["t"]); return "✅ 전송"
@feat("🔒 관리", "임베드 보내기", "제목/내용/색상 임베드", [P("t", "제목"), P("b", "내용", "str"), P("col", "색상 이름", required=False)], A)
async def _(i, a): await i.channel.send(embed=emb(a["t"], a["b"], COLORS.get(a["col"] or "", 0x5865F2))); return "✅ 전송"
@feat("🔒 관리", "DM 보내기", "멤버에게 DM", [PM, P("t", "내용", "str")], A, "dm")
async def _(i, a):
    try: await a["m"].send(f"📩 **{i.guild.name}** 관리자 메시지:\n{a['t']}")
    except discord.Forbidden: raise FeatErr("DM 차단됨")
    return "✅ DM 전송"
@feat("🔒 관리", "역할 전체 DM", "역할 멤버 전원 DM", [P("r", "역할", "role"), P("t", "내용", "str")], A)
async def _(i, a):
    await i.response.defer(ephemeral=True); n = 0
    for m in a["r"].members:
        try: await m.send(f"📩 **{i.guild.name}**:\n{a['t']}"); n += 1; await asyncio.sleep(0.5)
        except discord.Forbidden: pass
    return f"✅ {n}명 DM 전송"
@feat("🔒 관리", "반응 추가", "메시지에 이모지 반응", [P("id", "메시지 ID"), P("e", "이모지")], A)
async def _(i, a): m = await i.channel.fetch_message(int(a["id"])); await m.add_reaction(a["e"]); return "✅"
@feat("🔒 관리", "반응 전체 삭제", "메시지 반응 모두 제거", [P("id", "메시지 ID")], A)
async def _(i, a): m = await i.channel.fetch_message(int(a["id"])); await m.clear_reactions(); return "✅"
@feat("🔒 관리", "음성 강제 퇴장", "음성 채널에서 내보내기", [PM], A, "voice kick")
async def _(i, a): await a["m"].move_to(None); return f"🔇 {a['m'].mention} 음성 퇴장"
@feat("🔒 관리", "음성 마이크 음소거", "서버 마이크 음소거", [PM], A)
async def _(i, a): await a["m"].edit(mute=True); return "🎙️ 음소거"
@feat("🔒 관리", "음성 마이크 해제", "서버 마이크 음소거 해제", [PM], A)
async def _(i, a): await a["m"].edit(mute=False); return "🎙️ 해제"
@feat("🔒 관리", "음성 헤드셋 차단", "서버 헤드셋 차단", [PM], A)
async def _(i, a): await a["m"].edit(deafen=True); return "🎧 차단"
@feat("🔒 관리", "음성 헤드셋 해제", "서버 헤드셋 차단 해제", [PM], A)
async def _(i, a): await a["m"].edit(deafen=False); return "🎧 해제"
@feat("🔒 관리", "음성 채널 전원 퇴장", "지정 음성 채널 비우기", [P("c", "음성 채널", "channel")], A)
async def _(i, a):
    n = 0
    for m in list(getattr(a["c"], "members", [])): await m.move_to(None); n += 1
    return f"🔇 {n}명 퇴장"
@feat("🔒 관리", "초대 링크 생성", "현재 채널 초대 (시간/횟수)", [P("age", "유효 시간(분, 0=무제한)", "int", False, lo=0), P("uses", "사용 횟수(0=무제한)", "int", False, lo=0)], A, "invite")
async def _(i, a): inv = await i.channel.create_invite(max_age=(a["age"] or 0) * 60, max_uses=a["uses"] or 0); return f"🔗 {inv.url}"
@feat("🔒 관리", "초대 목록", "서버 초대 링크 목록", [], A)
async def _(i, a): invs = await i.guild.invites(); return emb("🔗 초대 목록", "\n".join(f"`{x.code}` {x.inviter} · {x.uses}회" for x in invs[:25]) or "없음")
@feat("🔒 관리", "초대 전체 삭제", "모든 초대 링크 삭제", [], A)
async def _(i, a):
    n = 0
    for inv in await i.guild.invites(): await inv.delete(); n += 1
    return f"🗑️ {n}개 삭제"
@feat("🔒 관리", "감사 로그 보기", "최근 감사 로그 15개", [], A, "audit")
async def _(i, a):
    rows = [x async for x in i.guild.audit_logs(limit=15)]
    return emb("📜 감사 로그", "\n".join(f"<t:{int(x.created_at.timestamp())}:R> {x.user} — {str(x.action).split('.')[-1]} → {x.target}" for x in rows) or "없음")
@feat("🔒 관리", "웹훅 목록", "채널 웹훅", [], A)
async def _(i, a): hs = await i.channel.webhooks(); return "\n".join(f"{h.name} ({h.id})" for h in hs) or "없음"
@feat("🔒 관리", "웹훅 생성", "채널 웹훅 생성", [P("t", "이름")], A)
async def _(i, a): h = await i.channel.create_webhook(name=a["t"]); return f"✅ 웹훅 생성\n||{h.url}||"
@feat("🔒 관리", "서버 이름 변경", "서버 이름 바꾸기", [P("t", "새 이름")], A)
async def _(i, a): await i.guild.edit(name=a["t"]); return f"✏️ 서버 → {a['t']}"
@feat("🔒 관리", "AFK 채널 설정", "잠수 채널·시간", [P("c", "음성 채널", "channel"), P("n", "분(1/5/15/30/60)", "int", lo=1, hi=60)], A)
async def _(i, a): await i.guild.edit(afk_channel=a["c"], afk_timeout=a["n"] * 60); return "✅ 설정"
@feat("🔒 관리", "시스템 채널 설정", "입장 메시지 채널", [P("c", "채널", "channel")], A)
async def _(i, a): await i.guild.edit(system_channel=a["c"]); return "✅ 설정"
@feat("🔒 관리", "인증 레벨 변경", "none/low/medium/high/highest", [P("l", "레벨", "choice", choices=["none", "low", "medium", "high", "highest"])], A)
async def _(i, a): await i.guild.edit(verification_level=getattr(discord.VerificationLevel, a["l"])); return f"✅ 인증 레벨 {a['l']}"
@feat("🔒 관리", "이모지 추가 (URL)", "이미지 URL로 이모지 추가", [P("t", "이름"), P("u", "이미지 URL")], A)
async def _(i, a):
    import aiohttp
    async with aiohttp.ClientSession() as s:
        async with s.get(a["u"]) as r: data = await r.read()
    e = await i.guild.create_custom_emoji(name=a["t"], image=data); return f"✅ {e}"
@feat("🔒 관리", "이모지 삭제", "이름으로 이모지 삭제", [P("t", "이름")], A)
async def _(i, a):
    e = discord.utils.get(i.guild.emojis, name=a["t"])
    if not e: raise FeatErr("이모지 없음")
    await e.delete(); return "🗑️ 삭제"
@feat("🔒 관리", "비활성 멤버 목록", "30일 넘게 역할 없는 멤버", [], A, "prune")
async def _(i, a): n = await i.guild.estimate_pruned_members(days=30); return f"👻 30일 비활성(역할 없음) 추정 {n}명"
@feat("🔒 관리", "비활성 멤버 정리", "30일 비활성 역할 없는 멤버 추방", [], A)
async def _(i, a): n = await i.guild.prune_members(days=30, compute_prune_count=True); return f"👢 {n}명 정리"
@feat("🔒 관리", "대량 밴 (ID 목록)", "쉼표로 구분한 ID 밴", [P("ids", "ID 목록", "list"), P("why", "사유", required=False)], A)
async def _(i, a):
    await i.response.defer(ephemeral=True); n = 0
    for s in a["ids"]:
        try: await i.guild.ban(discord.Object(int(s)), reason=a["why"] or "대량 밴"); n += 1
        except Exception: pass
    return f"🔨 {n}명 밴"
@feat("🔒 관리", "닉네임 전원 초기화", "모든 멤버 닉네임 제거", [], A)
async def _(i, a):
    await i.response.defer(ephemeral=True); n = 0
    for m in i.guild.members:
        if m.nick:
            try: await m.edit(nick=None); n += 1
            except discord.Forbidden: pass
    return f"✏️ {n}명 초기화"
@feat("🔒 관리", "멤버 음성 이동", "음성 채널로 이동", [PM, P("c", "음성 채널", "channel")], A)
async def _(i, a): await a["m"].move_to(a["c"]); return "✅ 이동"
@feat("🔒 관리", "역할 보유자 목록", "역할 멤버 목록", [P("r", "역할", "role")], A)
async def _(i, a): return emb(f"{a['r'].name} ({len(a['r'].members)}명)", ", ".join(m.display_name for m in a["r"].members[:60]) or "없음")
@feat("🔒 관리", "역할 없는 멤버", "역할이 하나도 없는 멤버", [], A)
async def _(i, a): ms = [m for m in i.guild.members if len(m.roles) == 1 and not m.bot]; return emb(f"역할 없음 ({len(ms)})", ", ".join(m.display_name for m in ms[:60]) or "없음")
@feat("🔒 관리", "신규 가입자 (7일)", "최근 7일 가입 멤버", [], A)
async def _(i, a):
    now = datetime.datetime.now(datetime.timezone.utc)
    ms = [m for m in i.guild.members if m.joined_at and (now - m.joined_at).days < 7]
    return emb(f"🆕 7일 내 가입 ({len(ms)})", "\n".join(f"{m.display_name} <t:{int(m.joined_at.timestamp())}:R>" for m in ms[:30]) or "없음")
@feat("🔒 관리", "계정 생성 7일 미만", "새 계정(의심) 목록", [], A)
async def _(i, a):
    now = datetime.datetime.now(datetime.timezone.utc)
    ms = [m for m in i.guild.members if (now - m.created_at).days < 7]
    return emb(f"⚠️ 새 계정 ({len(ms)})", ", ".join(m.display_name for m in ms[:60]) or "없음")
@feat("🔒 관리", "봇 목록", "서버의 봇들", [], A)
async def _(i, a): return ", ".join(m.display_name for m in i.guild.members if m.bot) or "없음"
@feat("🔒 관리", "타임아웃 중인 멤버", "현재 타임아웃 멤버", [], A)
async def _(i, a): ms = [m for m in i.guild.members if m.is_timed_out()]; return ", ".join(f"{m.display_name} (<t:{int(m.timed_out_until.timestamp())}:R>)" for m in ms) or "없음"
@feat("🔒 관리", "멤버 메모 추가", "관리자용 멤버 메모", [PM, P("t", "내용", "str")], A, "note")
async def _(i, a):
    n = (q1("SELECT COALESCE(MAX(idx),0) m FROM notes WHERE guild=? AND user=?", i.guild_id, a["m"].id)["m"] or 0) + 1
    ex("INSERT INTO notes VALUES(?,?,?,?)", i.guild_id, a["m"].id, n, a["t"]); return f"📝 메모 #{n} 저장"
@feat("🔒 관리", "멤버 메모 보기", "멤버 메모 목록", [PM], A)
async def _(i, a): return emb(f"📝 {a['m'].display_name} 메모", "\n".join(f"#{r['idx']} {r['text']}" for r in qa("SELECT * FROM notes WHERE guild=? AND user=? ORDER BY idx", i.guild_id, a["m"].id)) or "없음")
@feat("🔒 관리", "멤버 메모 삭제", "메모 전부 삭제", [PM], A)
async def _(i, a): ex("DELETE FROM notes WHERE guild=? AND user=?", i.guild_id, a["m"].id); return "✅ 삭제"

# ───────── 🔒 경고 ─────────
@feat("🔒 경고", "경고 주기", "경고 부여 (3회 1시간 타임아웃, 5회 추방)", [PM, P("why", "사유", required=False)], A, "warn")
async def _(i, a):
    ex("INSERT INTO warns(guild,user,mod,reason,ts) VALUES(?,?,?,?,?)", i.guild_id, a["m"].id, i.user.id, a["why"] or "사유 없음", int(time.time()))
    n = q1("SELECT COUNT(*) c FROM warns WHERE guild=? AND user=?", i.guild_id, a["m"].id)["c"]; extra = ""
    try:
        if n >= 5: await a["m"].kick(reason="경고 5회"); extra = " → 🚨 추방"
        elif n >= 3: await a["m"].timeout(datetime.timedelta(hours=1), reason="경고 3회"); extra = " → ⏱ 1시간 타임아웃"
    except discord.Forbidden: extra = " (자동 제재 권한 부족)"
    try: await a["m"].send(f"⚠️ **{i.guild.name}** 에서 경고를 받았어요 ({n}회): {a['why'] or '사유 없음'}")
    except discord.Forbidden: pass
    return f"⚠️ {a['m'].mention} 경고 **{n}회**{extra}"
@feat("🔒 경고", "경고 목록", "멤버 경고 내역", [PM], A)
async def _(i, a):
    rows = qa("SELECT * FROM warns WHERE guild=? AND user=? ORDER BY id", i.guild_id, a["m"].id)
    return emb(f"⚠️ {a['m'].display_name} 경고 {len(rows)}회", "\n".join(f"#{r['id']} <t:{r['ts']}:d> {r['reason']} (<@{r['mod']}>)" for r in rows[:20]) or "없음")
@feat("🔒 경고", "경고 삭제", "경고 번호로 삭제", [P("n", "경고 번호", "int")], A)
async def _(i, a): ex("DELETE FROM warns WHERE guild=? AND id=?", i.guild_id, a["n"]); return f"✅ 경고 #{a['n']} 삭제"
@feat("🔒 경고", "경고 초기화", "멤버 경고 전부 삭제", [PM], A)
async def _(i, a): ex("DELETE FROM warns WHERE guild=? AND user=?", i.guild_id, a["m"].id); return "✅ 초기화"
@feat("🔒 경고", "경고 전체 초기화", "서버 경고 전부 삭제", [], A)
async def _(i, a): ex("DELETE FROM warns WHERE guild=?", i.guild_id); return "✅ 서버 경고 초기화"
@feat("🔒 경고", "경고 랭킹", "경고 많은 순", [], A)
async def _(i, a): return emb("⚠️ 경고 랭킹", "\n".join(f"{n}. <@{r['user']}> {r['c']}회" for n, r in enumerate(qa("SELECT user, COUNT(*) c FROM warns WHERE guild=? GROUP BY user ORDER BY c DESC LIMIT 15", i.guild_id), 1)) or "없음")
@feat("🔒 경고", "경고 통계", "총 경고 수·인원", [], A)
async def _(i, a): r = q1("SELECT COUNT(*) c, COUNT(DISTINCT user) u FROM warns WHERE guild=?", i.guild_id); return f"⚠️ 총 {r['c']}회 / {r['u']}명"
@feat("🔒 경고", "최근 경고 10개", "서버 최근 경고", [], A)
async def _(i, a): return emb("⚠️ 최근 경고", "\n".join(f"<t:{r['ts']}:R> <@{r['user']}> — {r['reason']}" for r in qa("SELECT * FROM warns WHERE guild=? ORDER BY id DESC LIMIT 10", i.guild_id)) or "없음")
@feat("🔒 경고", "경고 + 타임아웃", "경고와 함께 N분 타임아웃", [PM, P("n", "분", "int", lo=1, hi=40320), P("why", "사유", required=False)], A)
async def _(i, a):
    ex("INSERT INTO warns(guild,user,mod,reason,ts) VALUES(?,?,?,?,?)", i.guild_id, a["m"].id, i.user.id, a["why"] or "사유 없음", int(time.time()))
    await a["m"].timeout(datetime.timedelta(minutes=a["n"]), reason=a["why"] or "경고"); return f"⚠️🔇 {a['m'].mention} 경고 + {a['n']}분"
@feat("🔒 경고", "경고 사유 수정", "경고 번호의 사유 변경", [P("n", "경고 번호", "int"), P("why", "새 사유")], A)
async def _(i, a): ex("UPDATE warns SET reason=? WHERE guild=? AND id=?", a["why"], i.guild_id, a["n"]); return "✅ 수정"
@feat("경고 조회", "내 경고 보기", "내가 받은 경고 (본인만)", [], False, "warn")
async def _(i, a):
    rows = qa("SELECT * FROM warns WHERE guild=? AND user=? ORDER BY id", i.guild_id, i.user.id)
    return emb(f"⚠️ 내 경고 {len(rows)}회", "\n".join(f"<t:{r['ts']}:d> {r['reason']}" for r in rows) or "경고 없음 ✨")
@feat("경고 조회", "내 경고 횟수", "경고 개수만", [])
async def _(i, a): return f"⚠️ 경고 {q1('SELECT COUNT(*) c FROM warns WHERE guild=? AND user=?', i.guild_id, i.user.id)['c']}회"

# ───────── 🔒 전투력 (수정은 관리자만) ─────────
@feat("🔒 전투력", "전투력 설정", "멤버 전투력 직접 설정", [PM, P("n", "값", "int", lo=0, hi=10_000_000)], A, "power 전투력")
async def _(i, a): return await change_power(i, a["m"], a["n"], "설정")
@feat("🔒 전투력", "전투력 추가", "멤버 전투력 +N", [PM, P("n", "값", "int", lo=1, hi=10_000_000)], A)
async def _(i, a): return await change_power(i, a["m"], mrow(i.guild_id, a["m"].id)["power"] + a["n"], f"+{a['n']:,}")
@feat("🔒 전투력", "전투력 감소", "멤버 전투력 -N", [PM, P("n", "값", "int", lo=1, hi=10_000_000)], A)
async def _(i, a): return await change_power(i, a["m"], mrow(i.guild_id, a["m"].id)["power"] - a["n"], f"-{a['n']:,}")
@feat("🔒 전투력", "전투력 초기화", "멤버 전투력 0", [PM], A)
async def _(i, a): return await change_power(i, a["m"], 0, "초기화")
@feat("🔒 전투력", "전투력 전원 초기화", "모든 클랜원 전투력 0", [], A)
async def _(i, a): ex("UPDATE members SET power=0 WHERE guild=?", i.guild_id); await refresh_board(i.guild); return "✅ 전원 전투력 초기화"
@feat("🔒 전투력", "전투력 전원 추가", "모든 클랜원 전투력 +N", [P("n", "값", "int", lo=1)], A)
async def _(i, a): ex("UPDATE members SET power=power+? WHERE guild=?", a["n"], i.guild_id); await refresh_board(i.guild); return f"✅ 전원 +{a['n']:,}"
@feat("🔒 전투력", "전투력 전원 비율 조정", "모든 전투력 × N% (시즌 리셋용)", [P("n", "퍼센트", "int", lo=0, hi=1000)], A)
async def _(i, a): ex("UPDATE members SET power=power*?/100 WHERE guild=?", a["n"], i.guild_id); await refresh_board(i.guild); return f"✅ 전원 {a['n']}% 적용"
@feat("🔒 전투력", "전투력 교환", "두 멤버 전투력 서로 바꾸기", [P("m", "멤버1", "member"), P("m2", "멤버2", "member")], A)
async def _(i, a):
    p1, p2 = mrow(i.guild_id, a["m"].id)["power"], mrow(i.guild_id, a["m2"].id)["power"]
    mset(i.guild_id, a["m"].id, "power", p2); mset(i.guild_id, a["m2"].id, "power", p1); await refresh_board(i.guild); return "✅ 교환 완료"
@feat("🔒 전투력", "전투력 복사", "멤버1 전투력을 멤버2에게", [P("m", "원본", "member"), P("m2", "대상", "member")], A)
async def _(i, a): return await change_power(i, a["m2"], mrow(i.guild_id, a["m"].id)["power"], "복사")
for _d in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
    for _sign in (1, -1):
        def _mk(d=_d, s=_sign):
            async def fn(i, a): return await change_power(i, a["m"], mrow(i.guild_id, a["m"].id)["power"] + s * d, f"{'+' if s > 0 else '-'}{d:,}")
            return fn
        add_feat("🔒 전투력", f"전투력 {'+' if _sign > 0 else '-'}{_d:,}", f"멤버 전투력 {'+' if _sign > 0 else '-'}{_d:,} 프리셋", _mk(), [PM], A, "power 프리셋")
async def record(i, m, win, n):
    c = cfg(i.guild_id); r = mrow(i.guild_id, m.id)
    if win: mset(i.guild_id, m.id, "wins", r["wins"] + n); d = c["win_pts"] * n
    else: mset(i.guild_id, m.id, "losses", r["losses"] + n); d = -c["loss_pts"] * n
    return await change_power(i, m, r["power"] + d, f"{'승리' if win else '패배'} {n}회 ({d:+,})")
@feat("🔒 전적", "승리 기록", "승리 N회 추가 (전투력 자동 반영)", [PM, P("n", "횟수", "int", False, lo=1, hi=100)], A, "win 전적")
async def _(i, a): return await record(i, a["m"], True, a["n"] or 1)
@feat("🔒 전적", "패배 기록", "패배 N회 추가 (전투력 자동 반영)", [PM, P("n", "횟수", "int", False, lo=1, hi=100)], A, "loss")
async def _(i, a): return await record(i, a["m"], False, a["n"] or 1)
for _n in (1, 2, 3, 5, 10):
    for _w in (True, False):
        def _mk(n=_n, w=_w):
            async def fn(i, a): return await record(i, a["m"], w, n)
            return fn
        add_feat("🔒 전적", f"{'승리' if _w else '패배'} {_n}회 기록", f"{'승' if _w else '패'} {_n}회 프리셋", _mk(), [PM], A, "전적 프리셋")
@feat("🔒 전적", "1v1 결과 기록", "승자/패자 동시 기록 + 매치 로그", [P("w", "승자", "member"), P("l", "패자", "member"), P("note", "메모", required=False)], A, "match 매치")
async def _(i, a):
    ex("INSERT INTO matches(guild,winner,loser,note,ts) VALUES(?,?,?,?,?)", i.guild_id, a["w"].id, a["l"].id, a["note"] or "", int(time.time()))
    await record(i, a["w"], True, 1); await record(i, a["l"], False, 1); return f"⚔️ {a['w'].mention} 승 / {a['l'].mention} 패 기록"
@feat("🔒 전적", "승수 설정", "승리 횟수 직접 설정", [PM, P("n", "값", "int", lo=0)], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "wins", a["n"]); return f"✅ {a['m'].mention} 승 {a['n']}"
@feat("🔒 전적", "패수 설정", "패배 횟수 직접 설정", [PM, P("n", "값", "int", lo=0)], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "losses", a["n"]); return f"✅ {a['m'].mention} 패 {a['n']}"
@feat("🔒 전적", "전적 초기화", "멤버 승/패 0", [PM], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "wins", 0); mset(i.guild_id, a["m"].id, "losses", 0); return "✅ 초기화"
@feat("🔒 전적", "전적 전원 초기화", "모든 클랜원 승/패 0", [], A)
async def _(i, a): ex("UPDATE members SET wins=0, losses=0 WHERE guild=?", i.guild_id); return "✅ 전원 전적 초기화"
@feat("🔒 전적", "매치 기록 삭제", "매치 번호로 삭제", [P("n", "매치 번호", "int")], A)
async def _(i, a): ex("DELETE FROM matches WHERE guild=? AND id=?", i.guild_id, a["n"]); return "✅ 삭제"
@feat("🔒 전적", "MVP 추가", "멤버 MVP +1", [PM], A, "mvp")
async def _(i, a): r = mrow(i.guild_id, a["m"].id); mset(i.guild_id, a["m"].id, "mvp", r["mvp"] + 1); return f"🏅 {a['m'].mention} MVP {r['mvp'] + 1}회"
@feat("🔒 전적", "MVP 설정", "MVP 횟수 설정", [PM, P("n", "값", "int", lo=0)], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "mvp", a["n"]); return "✅"
@feat("🔒 전적", "활동점수 추가", "활동점수 +N", [PM, P("n", "값", "int")], A, "activity")
async def _(i, a): r = mrow(i.guild_id, a["m"].id); mset(i.guild_id, a["m"].id, "activity", r["activity"] + a["n"]); return f"✅ 활동점수 {r['activity'] + a['n']}"
@feat("🔒 전적", "활동점수 설정", "활동점수 직접 설정", [PM, P("n", "값", "int", lo=0)], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "activity", a["n"]); return "✅"
@feat("🔒 전적", "활동점수 전원 초기화", "모두 0", [], A)
async def _(i, a): ex("UPDATE members SET activity=0 WHERE guild=?", i.guild_id); return "✅"

# ───────── 🔒 클랜 관리 ─────────
FIELDS = {"roblox": ("로블록스 닉", "str"), "main": ("주캐", "str"), "title": ("칭호", "str"), "memo": ("메모", "str"), "position": ("직책", "str"), "intro": ("소개", "str")}
for _f, (_lab, _k) in FIELDS.items():
    def _mk(f=_f, lab=_lab):
        async def fn(i, a): mset(i.guild_id, a["m"].id, f, a["v"]); return f"✅ {a['m'].mention} {lab} → {a['v']}"
        return fn
    def _mk2(f=_f, lab=_lab):
        async def fn(i, a): mset(i.guild_id, a["m"].id, f, None); return f"✅ {a['m'].mention} {lab} 초기화"
        return fn
    add_feat("🔒 클랜 관리", f"{_lab} 설정", f"멤버 {_lab} 설정", _mk(), [PM, P("v", _lab)], A, "클랜 필드")
    add_feat("🔒 클랜 관리", f"{_lab} 초기화", f"멤버 {_lab} 지우기", _mk2(), [PM], A)
for _pos in POSITIONS:
    def _mk(p=_pos):
        async def fn(i, a): mset(i.guild_id, a["m"].id, "position", p); return f"✅ {a['m'].mention} 직책 → {p}"
        return fn
    add_feat("🔒 클랜 관리", f"직책 {_pos} 임명", f"멤버를 {_pos}(으)로", _mk(), [PM], A, "position 직책")
for _c in CHAR_LIST:
    def _mk(c=_c):
        async def fn(i, a): mset(i.guild_id, a["m"].id, "main", c); return f"✅ {a['m'].mention} 주캐 → {c}"
        return fn
    add_feat("🔒 클랜 관리", f"주캐 지정: {_c}", f"멤버 주캐를 {_c}(으)로", _mk(), [PM], A, "main 주캐")
@feat("🔒 클랜 관리", "클랜원 등록", "닉/주캐/전투력 한 번에 등록", [PM, P("r", "로블록스 닉"), P("c", "주캐", required=False), P("p", "전투력", "int", False, lo=0)], A, "register")
async def _(i, a):
    mset(i.guild_id, a["m"].id, "roblox", a["r"])
    if a["c"]: mset(i.guild_id, a["m"].id, "main", a["c"])
    if a["p"] is not None: await change_power(i, a["m"], a["p"], "등록")
    return f"✅ {a['m'].mention} 등록 완료"
@feat("🔒 클랜 관리", "클랜원 제거", "클랜 기록 삭제", [PM], A)
async def _(i, a): ex("DELETE FROM members WHERE guild=? AND user=?", i.guild_id, a["m"].id); await refresh_board(i.guild); return "✅ 삭제"
@feat("🔒 클랜 관리", "탈퇴 멤버 정리", "서버에 없는 사람 기록 삭제", [], A)
async def _(i, a):
    n = 0
    for r in qa("SELECT user FROM members WHERE guild=?", i.guild_id):
        if not i.guild.get_member(r["user"]): ex("DELETE FROM members WHERE guild=? AND user=?", i.guild_id, r["user"]); n += 1
    await refresh_board(i.guild); return f"🧹 {n}명 정리"
@feat("🔒 클랜 관리", "가입 신청 목록", "대기 중인 가입 신청", [], A, "apply")
async def _(i, a): return emb("📥 가입 신청", "\n".join(f"<@{r['user']}> — `{r['roblox']}` {r['main'] or ''} <t:{r['ts']}:R>" for r in qa("SELECT * FROM applications WHERE guild=? ORDER BY ts", i.guild_id)) or "없음")
@feat("🔒 클랜 관리", "가입 승인", "신청 승인 → 클랜원 등록", [PM], A)
async def _(i, a):
    r = q1("SELECT * FROM applications WHERE guild=? AND user=?", i.guild_id, a["m"].id)
    if not r: raise FeatErr("신청 내역 없음")
    mset(i.guild_id, a["m"].id, "roblox", r["roblox"]); mset(i.guild_id, a["m"].id, "main", r["main"]); mset(i.guild_id, a["m"].id, "position", "신입")
    ex("DELETE FROM applications WHERE guild=? AND user=?", i.guild_id, a["m"].id)
    try: await a["m"].send(f"🎉 **{i.guild.name}** 클랜 가입이 승인되었어요!")
    except discord.Forbidden: pass
    return f"✅ {a['m'].mention} 승인"
@feat("🔒 클랜 관리", "가입 거절", "신청 거절", [PM, P("why", "사유", required=False)], A)
async def _(i, a):
    ex("DELETE FROM applications WHERE guild=? AND user=?", i.guild_id, a["m"].id)
    try: await a["m"].send(f"😢 **{i.guild.name}** 클랜 가입이 거절되었어요. {a['why'] or ''}")
    except discord.Forbidden: pass
    return "✅ 거절"
@feat("🔒 클랜 관리", "가입 전원 승인", "대기 신청 모두 승인", [], A)
async def _(i, a):
    n = 0
    for r in qa("SELECT * FROM applications WHERE guild=?", i.guild_id):
        mset(i.guild_id, r["user"], "roblox", r["roblox"]); mset(i.guild_id, r["user"], "main", r["main"]); mset(i.guild_id, r["user"], "position", "신입"); n += 1
    ex("DELETE FROM applications WHERE guild=?", i.guild_id); return f"✅ {n}명 승인"
@feat("🔒 클랜 관리", "출석 횟수 설정", "멤버 출석 일수 설정", [PM, P("n", "값", "int", lo=0)], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "attend", a["n"]); return "✅"
@feat("🔒 클랜 관리", "데이터 내보내기 (CSV)", "클랜원 데이터 CSV 파일", [], A, "export")
async def _(i, a):
    import io
    rows = qa("SELECT * FROM members WHERE guild=? ORDER BY power DESC", i.guild_id)
    s = "user,name,roblox,main,power,wins,losses,title,position,mvp,activity,attend\n" + "\n".join(
        f"{r['user']},{name_of(i.guild, r['user'])},{r['roblox'] or ''},{r['main'] or ''},{r['power']},{r['wins']},{r['losses']},{r['title'] or ''},{r['position'] or ''},{r['mvp']},{r['activity']},{r['attend']}" for r in rows)
    await i.response.send_message(file=discord.File(io.BytesIO(s.encode("utf-8-sig")), "clan.csv"), ephemeral=True)
@feat("🔒 클랜 관리", "일괄 전투력 입력", "닉:전투력 쉼표 구분 (예: 철수:1200, 영희:800)", [P("l", "목록", "list")], A, "bulk")
async def _(i, a):
    ok, bad = 0, []
    for item in a["l"]:
        if ":" not in item: bad.append(item); continue
        n, v = item.rsplit(":", 1)
        try: m = parse_member(i, n); mset(i.guild_id, m.id, "power", int(v)); ok += 1
        except Exception: bad.append(item)
    await refresh_board(i.guild); return f"✅ {ok}명 적용" + (f" / 실패: {', '.join(bad)}" if bad else "")

# ───────── 🔒 랭킹표 게시판 ─────────
@feat("🔒 랭킹표", "랭킹표 채널 설정", "자동 갱신 랭킹표를 게시할 채널", [P("c", "채널", "channel")], A, "board leaderboard")
async def _(i, a): set_cfg(i.guild_id, "board_ch", a["c"].id); set_cfg(i.guild_id, "board_msg", None); await refresh_board(i.guild); return f"✅ 랭킹표 → {a['c'].mention}"
@feat("🔒 랭킹표", "랭킹표 지금 갱신", "랭킹표 수동 갱신", [], A)
async def _(i, a): await refresh_board(i.guild); return "✅ 갱신"
@feat("🔒 랭킹표", "랭킹표 제목 설정", "랭킹표 제목", [P("t", "제목")], A)
async def _(i, a): set_cfg(i.guild_id, "board_title", a["t"]); await refresh_board(i.guild); return "✅"
@feat("🔒 랭킹표", "랭킹표 표시 인원", "상위 N명 표시 (1~30)", [P("n", "인원", "int", lo=1, hi=30)], A)
async def _(i, a): set_cfg(i.guild_id, "board_n", a["n"]); await refresh_board(i.guild); return "✅"
for _k, _lab in RANK_KEYS.items():
    def _mk(k=_k, lab=_lab):
        async def fn(i, a): set_cfg(i.guild_id, "board_sort", k); await refresh_board(i.guild); return f"✅ 랭킹표 정렬 → {lab}"
        return fn
    add_feat("🔒 랭킹표", f"랭킹표 정렬: {_lab}", f"랭킹표를 {_lab} 기준으로", _mk(), [], A, "board sort")
@feat("🔒 랭킹표", "랭킹표 해제", "자동 갱신 중단", [], A)
async def _(i, a): set_cfg(i.guild_id, "board_ch", None); return "✅ 해제"
@feat("🔒 랭킹표", "랭킹표 현재 채널에 게시", "여기에 랭킹표 1회 게시 (갱신 안 됨)", [], A)
async def _(i, a): await i.channel.send(embed=rank_embed(i.guild, "power", "⚔️ 전투력 랭킹", 1, 20)); return "✅ 게시"
@feat("🔒 랭킹표", "티어 분포 게시", "티어별 인원 공개 게시", [], A)
async def _(i, a):
    rows = qa("SELECT power FROM members WHERE guild=?", i.guild_id); cnt = {t[1]: 0 for t in TIERS}
    for r in rows: cnt[tier_of(r["power"])[1]] += 1
    await i.channel.send(embed=emb("🏆 티어 분포", "\n".join(f"{t[2]} {t[1]}: {cnt[t[1]]}명" for t in reversed(TIERS)))); return "✅"

# ───────── 🔒 칭호 ─────────
@feat("🔒 칭호", "칭호 생성", "칭호 목록에 추가", [P("t", "칭호")], A, "title")
async def _(i, a): ex("INSERT OR IGNORE INTO titles VALUES(?,?)", i.guild_id, a["t"]); return f"✅ 칭호 `{a['t']}` 생성"
@feat("🔒 칭호", "칭호 삭제", "칭호 목록에서 제거", [P("t", "칭호")], A)
async def _(i, a): ex("DELETE FROM titles WHERE guild=? AND name=?", i.guild_id, a["t"]); return "✅ 삭제"
@feat("🔒 칭호", "칭호 부여", "멤버에게 칭호", [PM, P("t", "칭호")], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "title", a["t"]); return f"🏷️ {a['m'].mention} ← {a['t']}"
@feat("🔒 칭호", "칭호 회수", "멤버 칭호 제거", [PM], A)
async def _(i, a): mset(i.guild_id, a["m"].id, "title", None); return "✅ 회수"
@feat("🔒 칭호", "칭호 일괄 부여", "역할 멤버 전원에게 칭호", [P("r", "역할", "role"), P("t", "칭호")], A)
async def _(i, a):
    for m in a["r"].members: mset(i.guild_id, m.id, "title", a["t"])
    return f"✅ {len(a['r'].members)}명 부여"
@feat("🔒 칭호", "칭호 전원 회수", "모든 칭호 제거", [], A)
async def _(i, a): ex("UPDATE members SET title=NULL WHERE guild=?", i.guild_id); return "✅"
for _t in ["에이스", "MVP", "베테랑", "신입왕", "콤보 장인", "티밍 파괴자", "불사신", "저격수", "탱커", "스피드스타", "전략가", "분위기 메이커"]:
    def _mk(t=_t):
        async def fn(i, a): mset(i.guild_id, a["m"].id, "title", t); return f"🏷️ {a['m'].mention} ← {t}"
        return fn
    add_feat("🔒 칭호", f"칭호 부여: {_t}", f"'{_t}' 칭호 지급", _mk(), [PM], A, "title 칭호")
@feat("칭호", "칭호 목록", "등록된 칭호", [])
async def _(i, a): return "🏷️ " + (", ".join(r["name"] for r in qa("SELECT name FROM titles WHERE guild=?", i.guild_id)) or "없음")
@feat("칭호", "칭호 보유자", "특정 칭호 가진 멤버", [P("t", "칭호")])
async def _(i, a): return ", ".join(name_of(i.guild, r["user"]) for r in qa("SELECT user FROM members WHERE guild=? AND title=?", i.guild_id, a["t"])) or "없음"
@feat("칭호", "내 칭호", "내 칭호 확인", [])
async def _(i, a): return f"🏷️ {mrow(i.guild_id, i.user.id)['title'] or '칭호 없음'}"
@feat("칭호", "칭호 전체 현황", "누가 어떤 칭호", [])
async def _(i, a): return emb("🏷️ 칭호 현황", "\n".join(f"{name_of(i.guild, r['user'])} — {r['title']}" for r in qa("SELECT user,title FROM members WHERE guild=? AND title IS NOT NULL", i.guild_id)[:40]) or "없음")

# ───────── 이벤트 ─────────
@feat("🔒 이벤트", "이벤트 생성", "새 이벤트 열기", [P("t", "이름"), P("d", "설명", "str", False)], A, "event")
async def _(i, a):
    ex("INSERT INTO events(guild,name,desc,ts) VALUES(?,?,?,?)", i.guild_id, a["t"], a["d"] or "", int(time.time()))
    eid = q1("SELECT MAX(id) m FROM events WHERE guild=?", i.guild_id)["m"]
    await i.channel.send(embed=emb(f"🎉 이벤트 #{eid}: {a['t']}", (a["d"] or "") + "\n\n패널 → 검색 '이벤트 참가' 로 참가하세요!", 0xF39C12)); return f"✅ 이벤트 #{eid} 생성"
@feat("🔒 이벤트", "이벤트 종료", "이벤트 닫기", [P("n", "이벤트 번호", "int")], A)
async def _(i, a): ex("UPDATE events SET open=0 WHERE guild=? AND id=?", i.guild_id, a["n"]); return "✅ 종료"
@feat("🔒 이벤트", "이벤트 삭제", "이벤트 삭제", [P("n", "이벤트 번호", "int")], A)
async def _(i, a): ex("DELETE FROM events WHERE guild=? AND id=?", i.guild_id, a["n"]); ex("DELETE FROM event_join WHERE event=?", a["n"]); return "✅ 삭제"
@feat("🔒 이벤트", "우승자 지정", "이벤트 우승자 + 포인트 보상", [P("n", "이벤트 번호", "int"), PM, P("p", "보상 포인트", "int", False, lo=0)], A)
async def _(i, a):
    ex("UPDATE events SET winner=?, open=0 WHERE guild=? AND id=?", a["m"].id, i.guild_id, a["n"])
    if a["p"]: add_pts(i.guild_id, a["m"].id, a["p"])
    await i.channel.send(f"🏆 이벤트 #{a['n']} 우승: {a['m'].mention}" + (f" (+{a['p']}P)" if a["p"] else "")); return "✅"
@feat("🔒 이벤트", "참가자 랜덤 추첨", "이벤트 참가자 중 N명 추첨", [P("n", "이벤트 번호", "int"), P("k", "인원", "int", False, lo=1, hi=20)], A)
async def _(i, a):
    us = [r["user"] for r in qa("SELECT user FROM event_join WHERE event=?", a["n"])]
    if not us: raise FeatErr("참가자 없음")
    pick = random.sample(us, min(a["k"] or 1, len(us))); return "🎉 당첨: " + ", ".join(f"<@{u}>" for u in pick)
@feat("🔒 이벤트", "참가자 전원 포인트", "이벤트 참가자 전원 +P", [P("n", "이벤트 번호", "int"), P("p", "포인트", "int")], A)
async def _(i, a):
    us = qa("SELECT user FROM event_join WHERE event=?", a["n"])
    for r in us: add_pts(i.guild_id, r["user"], a["p"])
    return f"✅ {len(us)}명 +{a['p']}P"
@feat("🔒 이벤트", "참가자 강제 제거", "이벤트에서 멤버 제거", [P("n", "이벤트 번호", "int"), PM], A)
async def _(i, a): ex("DELETE FROM event_join WHERE event=? AND user=?", a["n"], a["m"].id); return "✅"
@feat("이벤트", "이벤트 목록", "진행 중 이벤트", [])
async def _(i, a): return emb("🎉 이벤트", "\n".join(f"#{r['id']} **{r['name']}** {'🟢' if r['open'] else '🔴'} — {r['desc'][:50]}" for r in qa("SELECT * FROM events WHERE guild=? ORDER BY id DESC LIMIT 15", i.guild_id)) or "없음")
@feat("이벤트", "이벤트 참가", "번호로 참가", [P("n", "이벤트 번호", "int")])
async def _(i, a):
    e = q1("SELECT * FROM events WHERE guild=? AND id=?", i.guild_id, a["n"])
    if not e or not e["open"]: raise FeatErr("열려있는 이벤트가 아니에요")
    ex("INSERT OR IGNORE INTO event_join VALUES(?,?)", a["n"], i.user.id); return f"✅ #{a['n']} {e['name']} 참가!"
@feat("이벤트", "이벤트 참가 취소", "참가 취소", [P("n", "이벤트 번호", "int")])
async def _(i, a): ex("DELETE FROM event_join WHERE event=? AND user=?", a["n"], i.user.id); return "✅ 취소"
@feat("이벤트", "이벤트 참가자", "참가자 목록", [P("n", "이벤트 번호", "int")])
async def _(i, a): us = qa("SELECT user FROM event_join WHERE event=?", a["n"]); return f"👥 {len(us)}명: " + (", ".join(name_of(i.guild, r["user"]) for r in us[:50]) or "없음")
@feat("이벤트", "이벤트 상세", "이벤트 정보", [P("n", "이벤트 번호", "int")])
async def _(i, a):
    e = q1("SELECT * FROM events WHERE guild=? AND id=?", i.guild_id, a["n"])
    if not e: raise FeatErr("없음")
    return emb(f"#{e['id']} {e['name']}", f"{e['desc']}\n상태: {'진행 중' if e['open'] else '종료'}\n우승: {('<@%d>' % e['winner']) if e['winner'] else '-'}\n참가 {q1('SELECT COUNT(*) c FROM event_join WHERE event=?', a['n'])['c']}명")
@feat("이벤트", "내 참가 이벤트", "내가 참가한 이벤트", [])
async def _(i, a): return ", ".join(f"#{r['event']}" for r in qa("SELECT event FROM event_join WHERE user=?", i.user.id)) or "없음"
@feat("이벤트", "역대 우승자", "이벤트 우승 기록", [])
async def _(i, a): return emb("🏆 역대 우승", "\n".join(f"#{r['id']} {r['name']} — <@{r['winner']}>" for r in qa("SELECT * FROM events WHERE guild=? AND winner IS NOT NULL ORDER BY id DESC LIMIT 20", i.guild_id)) or "없음")

# ───────── 스쿼드 ─────────
def my_squad(g, u): r = q1("SELECT name FROM squad_mem WHERE guild=? AND user=?", g, u); return r["name"] if r else None
@feat("🔒 스쿼드", "스쿼드 생성", "스쿼드(소규모 팀) 생성, 리더 지정", [P("t", "이름"), P("m", "리더", "member")], A, "squad team 팀")
async def _(i, a):
    ex("INSERT OR IGNORE INTO squads VALUES(?,?,?)", i.guild_id, a["t"], a["m"].id); ex("INSERT OR REPLACE INTO squad_mem VALUES(?,?,?)", i.guild_id, a["t"], a["m"].id); return f"✅ 스쿼드 `{a['t']}` 생성 (리더 {a['m'].mention})"
@feat("🔒 스쿼드", "스쿼드 해체", "스쿼드 삭제", [P("t", "이름")], A)
async def _(i, a): ex("DELETE FROM squads WHERE guild=? AND name=?", i.guild_id, a["t"]); ex("DELETE FROM squad_mem WHERE guild=? AND name=?", i.guild_id, a["t"]); return "✅ 해체"
@feat("🔒 스쿼드", "스쿼드 배정", "멤버를 스쿼드에 넣기", [PM, P("t", "스쿼드")], A)
async def _(i, a):
    if not q1("SELECT 1 FROM squads WHERE guild=? AND name=?", i.guild_id, a["t"]): raise FeatErr("없는 스쿼드")
    ex("INSERT OR REPLACE INTO squad_mem VALUES(?,?,?)", i.guild_id, a["t"], a["m"].id); return f"✅ {a['m'].mention} → {a['t']}"
@feat("🔒 스쿼드", "스쿼드 제외", "멤버를 스쿼드에서 빼기", [PM], A)
async def _(i, a): ex("DELETE FROM squad_mem WHERE guild=? AND user=?", i.guild_id, a["m"].id); return "✅"
@feat("🔒 스쿼드", "스쿼드 리더 변경", "리더 교체", [P("t", "스쿼드"), PM], A)
async def _(i, a): ex("UPDATE squads SET leader=? WHERE guild=? AND name=?", a["m"].id, i.guild_id, a["t"]); return "✅"
@feat("🔒 스쿼드", "스쿼드 자동 편성", "등록 클랜원을 N개 스쿼드로 전투력 균등 배분", [P("n", "스쿼드 수", "int", lo=2, hi=10)], A)
async def _(i, a):
    rows = qa("SELECT user, power FROM members WHERE guild=? AND roblox IS NOT NULL ORDER BY power DESC", i.guild_id)
    if len(rows) < a["n"]: raise FeatErr("클랜원이 부족해요")
    ex("DELETE FROM squads WHERE guild=?", i.guild_id); ex("DELETE FROM squad_mem WHERE guild=?", i.guild_id)
    teams = [[] for _ in range(a["n"])]
    for k, r in enumerate(rows): teams[k % a["n"] if (k // a["n"]) % 2 == 0 else a["n"] - 1 - k % a["n"]].append(r)
    for k, t in enumerate(teams, 1):
        ex("INSERT INTO squads VALUES(?,?,?)", i.guild_id, f"{k}팀", t[0]["user"])
        for r in t: ex("INSERT INTO squad_mem VALUES(?,?,?)", i.guild_id, f"{k}팀", r["user"])
    return emb("✅ 자동 편성", "\n".join(f"**{k}팀** ({sum(r['power'] for r in t):,}) — " + ", ".join(name_of(i.guild, r["user"]) for r in t) for k, t in enumerate(teams, 1)))
@feat("스쿼드", "스쿼드 목록", "모든 스쿼드", [])
async def _(i, a): return emb("👥 스쿼드", "\n".join(f"**{r['name']}** (리더 {name_of(i.guild, r['leader'])}) — {q1('SELECT COUNT(*) c FROM squad_mem WHERE guild=? AND name=?', i.guild_id, r['name'])['c']}명" for r in qa("SELECT * FROM squads WHERE guild=?", i.guild_id)) or "없음")
@feat("스쿼드", "스쿼드 멤버", "스쿼드 구성원", [P("t", "스쿼드")])
async def _(i, a): return ", ".join(name_of(i.guild, r["user"]) for r in qa("SELECT user FROM squad_mem WHERE guild=? AND name=?", i.guild_id, a["t"])) or "없음"
@feat("스쿼드", "내 스쿼드", "내가 속한 스쿼드", [])
async def _(i, a): return f"👥 {my_squad(i.guild_id, i.user.id) or '소속 없음'}"
@feat("스쿼드", "스쿼드 랭킹", "스쿼드 총 전투력 순", [])
async def _(i, a):
    rows = qa("SELECT s.name, SUM(m.power) p, COUNT(*) c FROM squad_mem s JOIN members m ON m.guild=s.guild AND m.user=s.user WHERE s.guild=? GROUP BY s.name ORDER BY p DESC", i.guild_id)
    return emb("🏆 스쿼드 랭킹", "\n".join(f"{n}. **{r['name']}** — {r['p']:,} ({r['c']}명)" for n, r in enumerate(rows, 1)) or "없음")
@feat("스쿼드", "스쿼드 평균 전투력", "스쿼드별 평균", [])
async def _(i, a):
    rows = qa("SELECT s.name, AVG(m.power) p FROM squad_mem s JOIN members m ON m.guild=s.guild AND m.user=s.user WHERE s.guild=? GROUP BY s.name ORDER BY p DESC", i.guild_id)
    return "\n".join(f"{r['name']}: {int(r['p']):,}" for r in rows) or "없음"

# ───────── 클랜 (조회) ─────────
@feat("클랜", "내 정보", "내 프로필 (전투력·티어·전적)", [], False, "profile me 프로필")
async def _(i, a): return profile_embed(i.guild, i.user)
@feat("클랜", "멤버 정보", "다른 클랜원 프로필", [PM])
async def _(i, a): return profile_embed(i.guild, a["m"])
@feat("클랜", "가입 신청", "클랜 가입 신청 (관리자 승인 필요)", [P("r", "로블록스 닉"), P("c", "주캐", required=False)], False, "apply join")
async def _(i, a):
    ex("INSERT OR REPLACE INTO applications VALUES(?,?,?,?,?)", i.guild_id, i.user.id, a["r"], a["c"], int(time.time()))
    await log(i.guild, emb("📥 가입 신청", f"{i.user.mention} — `{a['r']}` {a['c'] or ''}", 0x3498DB)); return "✅ 신청 완료! 관리자 승인을 기다려주세요."
@feat("클랜", "정보 수정 요청", "닉/주캐 변경을 관리자에게 요청", [P("t", "변경 내용", "str")])
async def _(i, a): await log(i.guild, emb("✏️ 정보 수정 요청", f"{i.user.mention}: {a['t']}", 0x3498DB)); return "✅ 관리자에게 전달했어요."
@feat("클랜", "클랜원 명단", "등록 클랜원 (전투력 순)", [], False, "list members")
async def _(i, a):
    rows = qa("SELECT * FROM members WHERE guild=? AND roblox IS NOT NULL ORDER BY power DESC", i.guild_id)
    return emb(f"📋 클랜원 명단 ({len(rows)}명)", "\n".join(f"{name_of(i.guild, r['user'])} — `{r['roblox']}` {r['main'] or ''} ({r['power']:,})" for r in rows[:40]) or "없음")
@feat("클랜", "직책별 명단", "단장/부단장/간부… 별 명단", [])
async def _(i, a):
    e = emb("👑 직책")
    for p in POSITIONS:
        ms = [name_of(i.guild, r["user"]) for r in qa("SELECT user FROM members WHERE guild=? AND position=?", i.guild_id, p)]
        if ms: e.add_field(name=p, value=", ".join(ms)[:1000], inline=False)
    return e
@feat("클랜", "클랜 통계", "인원·총 전투력·전적", [], False, "stats")
async def _(i, a):
    r = q1("SELECT COUNT(*) n, SUM(power) p, AVG(power) av, SUM(wins) w, SUM(losses) l, MAX(power) mx FROM members WHERE guild=?", i.guild_id)
    e = emb("📈 클랜 통계", color=0x1ABC9C)
    for k, v in [("등록 인원", r["n"] or 0), ("총 전투력", f"{r['p'] or 0:,}"), ("평균 전투력", f"{int(r['av'] or 0):,}"), ("최고 전투력", f"{r['mx'] or 0:,}"), ("총 전적", f"{r['w'] or 0}승 {r['l'] or 0}패")]: e.add_field(name=k, value=str(v))
    return e
@feat("클랜", "클랜 소개", "클랜 소개문 보기", [])
async def _(i, a): c = cfg(i.guild_id); return emb(f"⚔️ {c['clan_name'] or i.guild.name}", c["clan_desc"] or "소개가 아직 없어요.")
@feat("클랜", "클랜 규칙", "클랜 규칙 보기", [], False, "rules")
async def _(i, a): return emb("📜 클랜 규칙", cfg(i.guild_id)["clan_rules"] or "규칙이 아직 없어요.")
@feat("클랜", "주캐 분포", "주캐별 인원", [])
async def _(i, a): return emb("🎭 주캐 분포", "\n".join(f"**{r['main']}** — {r['c']}명 {'▰' * min(r['c'], 20)}" for r in qa("SELECT main, COUNT(*) c FROM members WHERE guild=? AND main IS NOT NULL GROUP BY main ORDER BY c DESC", i.guild_id)) or "없음")
@feat("클랜", "티어 분포", "티어별 인원", [])
async def _(i, a):
    cnt = {t[1]: 0 for t in TIERS}
    for r in qa("SELECT power FROM members WHERE guild=?", i.guild_id): cnt[tier_of(r["power"])[1]] += 1
    return emb("🏆 티어 분포", "\n".join(f"{t[2]} {t[1]}: {cnt[t[1]]}명" for t in reversed(TIERS)))
@feat("클랜", "로블록스 프로필 검색", "멤버 로블록스 프로필 링크", [P("m", "멤버", "member", False)])
async def _(i, a):
    m = a["m"] or i.user; r = mrow(i.guild_id, m.id)
    if not r["roblox"]: raise FeatErr("로블록스 닉이 등록되지 않았어요")
    return f"🔗 **{r['roblox']}** → https://www.roblox.com/search/users?keyword={urllib.parse.quote(r['roblox'])}"
@feat("클랜", "로블록스 닉으로 찾기", "로블록스 닉 → 디스코드 멤버", [P("r", "로블록스 닉")])
async def _(i, a): rows = qa("SELECT user FROM members WHERE guild=? AND lower(roblox)=lower(?)", i.guild_id, a["r"]); return ", ".join(f"<@{r['user']}>" for r in rows) or "없음"
@feat("클랜", "매치 기록", "최근 1v1 기록", [], False, "match")
async def _(i, a): return emb("⚔️ 최근 매치", "\n".join(f"#{r['id']} <t:{r['ts']}:d> {name_of(i.guild, r['winner'])} 승 vs {name_of(i.guild, r['loser'])} {r['note']}" for r in qa("SELECT * FROM matches WHERE guild=? ORDER BY id DESC LIMIT 15", i.guild_id)) or "없음")
@feat("클랜", "내 매치 기록", "내가 포함된 매치", [])
async def _(i, a): return emb("⚔️ 내 매치", "\n".join(f"<t:{r['ts']}:d> {'승 vs ' + name_of(i.guild, r['loser']) if r['winner'] == i.user.id else '패 vs ' + name_of(i.guild, r['winner'])}" for r in qa("SELECT * FROM matches WHERE guild=? AND (winner=? OR loser=?) ORDER BY id DESC LIMIT 15", i.guild_id, i.user.id, i.user.id)) or "없음")
@feat("클랜", "상대 전적", "나 vs 특정 멤버 상대 전적", [PM], False, "h2h")
async def _(i, a):
    w = q1("SELECT COUNT(*) c FROM matches WHERE guild=? AND winner=? AND loser=?", i.guild_id, i.user.id, a["m"].id)["c"]
    l = q1("SELECT COUNT(*) c FROM matches WHERE guild=? AND winner=? AND loser=?", i.guild_id, a["m"].id, i.user.id)["c"]
    return f"⚔️ 나 vs {a['m'].display_name}: **{w}승 {l}패**"
@feat("클랜", "멤버 비교", "두 멤버 전투력/전적 비교", [P("m", "멤버1", "member"), P("m2", "멤버2", "member")], False, "compare")
async def _(i, a):
    r1, r2 = mrow(i.guild_id, a["m"].id), mrow(i.guild_id, a["m2"].id)
    e = emb(f"⚖️ {a['m'].display_name} vs {a['m2'].display_name}")
    for k, lab in [("power", "전투력"), ("wins", "승"), ("losses", "패"), ("mvp", "MVP"), ("activity", "활동")]: e.add_field(name=lab, value=f"{r1[k]:,} | {r2[k]:,}")
    return e
@feat("클랜", "나와 비슷한 전투력", "내 전투력 ±20% 멤버", [])
async def _(i, a):
    p = mrow(i.guild_id, i.user.id)["power"]
    rows = qa("SELECT * FROM members WHERE guild=? AND user!=? AND power BETWEEN ? AND ? ORDER BY ABS(power-?) LIMIT 10", i.guild_id, i.user.id, int(p * 0.8), int(p * 1.2) + 1, p)
    return emb("🤝 비슷한 전투력", "\n".join(fmt_member(i.guild, r) for r in rows) or "없음")
@feat("클랜", "승률 계산", "내 승률", [])
async def _(i, a): r = mrow(i.guild_id, i.user.id); g = r["wins"] + r["losses"]; return f"📊 {r['wins']}승 {r['losses']}패 — 승률 {(r['wins'] * 100 / g) if g else 0:.1f}%"
@feat("클랜", "다음 티어까지", "승급에 필요한 전투력", [])
async def _(i, a):
    p = mrow(i.guild_id, i.user.id)["power"]; nt = next_tier(p); c = cfg(i.guild_id)
    if not nt: return "🌟 이미 최고 티어!"
    need = nt[0] - p; return f"⬆️ {nt[2]} {nt[1]}까지 **{need:,}** (승리 약 {math.ceil(need / max(1, c['win_pts']))}회)"
@feat("클랜", "활동 점수 보기", "내 활동점수·MVP", [])
async def _(i, a): r = mrow(i.guild_id, i.user.id); return f"⭐ 활동점수 {r['activity']} · MVP {r['mvp']}회 · 출석 {r['attend']}일"
@feat("클랜", "가입일 확인", "클랜 등록일", [P("m", "멤버", "member", False)])
async def _(i, a): m = a["m"] or i.user; return f"📅 <t:{mrow(i.guild_id, m.id)['joined']}:D> 등록"
@feat("클랜", "클랜 가입 순서", "등록 순 명단", [])
async def _(i, a): return emb("📅 가입 순", "\n".join(f"{n}. {name_of(i.guild, r['user'])} <t:{r['joined']}:d>" for n, r in enumerate(qa("SELECT * FROM members WHERE guild=? AND roblox IS NOT NULL ORDER BY joined LIMIT 30", i.guild_id), 1)) or "없음")

# ───────── 랭킹 ─────────
for _k, _lab in RANK_KEYS.items():
    def _mk(k=_k, lab=_lab):
        async def fn(i, a): return rank_embed(i.guild, k, f"🏆 {lab} 랭킹", a["p"] or 1)
        return fn
    def _mk10(k=_k, lab=_lab):
        async def fn(i, a): return rank_embed(i.guild, k, f"🏆 {lab} TOP 10", 1)
        return fn
    def _mk3(k=_k, lab=_lab):
        async def fn(i, a): return rank_embed(i.guild, k, f"🏆 {lab} TOP 3", 1, 3)
        return fn
    def _mkme(k=_k, lab=_lab):
        async def fn(i, a):
            rows = [r for r in qa(f"SELECT * FROM members WHERE guild=? ORDER BY {k} DESC, power DESC", i.guild_id) if r[k] > 0]
            idx = next((n for n, r in enumerate(rows) if r["user"] == i.user.id), None)
            if idx is None: return f"아직 {lab} 기록이 없어요."
            lo, hi = max(0, idx - 3), idx + 4
            return emb(f"📍 내 주변 {lab} 순위", "\n".join(f"{'👉' if n == idx else '　'} `{n + 1}.` {name_of(i.guild, r['user'])} — {r[k]:,}" for n, r in enumerate(rows[lo:hi], start=lo)))
        return fn
    add_feat("랭킹", f"{_lab} 랭킹", f"{_lab} 순위표 (페이지)", _mk(), [P("p", "페이지", "int", False, lo=1, hi=100)], False, "rank 순위")
    add_feat("랭킹", f"{_lab} TOP 10", f"{_lab} 상위 10명", _mk10(), [], False, "rank top")
    add_feat("랭킹", f"{_lab} TOP 3", f"{_lab} 상위 3명", _mk3(), [], False, "rank top")
    add_feat("랭킹", f"내 주변 {_lab} 순위", f"{_lab} 내 앞뒤 3명", _mkme(), [], False, "rank me")
@feat("랭킹", "내 순위", "내 전투력 순위", [], False, "rank me")
async def _(i, a): r = mrow(i.guild_id, i.user.id); return f"📊 전투력 순위 **#{q1('SELECT COUNT(*)+1 c FROM members WHERE guild=? AND power>?', i.guild_id, r['power'])['c']}** ({r['power']:,})"
@feat("랭킹", "승률 랭킹", "승률 순 (5경기 이상)", [])
async def _(i, a):
    rows = [r for r in qa("SELECT * FROM members WHERE guild=?", i.guild_id) if r["wins"] + r["losses"] >= 5]
    rows.sort(key=lambda r: -r["wins"] / (r["wins"] + r["losses"]))
    return emb("📊 승률 랭킹", "\n".join(f"`{n}.` {name_of(i.guild, r['user'])} — {r['wins'] * 100 / (r['wins'] + r['losses']):.0f}% ({r['wins']}승 {r['losses']}패)" for n, r in enumerate(rows[:15], 1)) or "5경기 이상 멤버 없음")
@feat("랭킹", "포인트 랭킹", "포인트 TOP 15", [], False, "points")
async def _(i, a): return emb("💰 포인트 랭킹", "\n".join(f"`{n}.` {name_of(i.guild, r['user'])} — {r['pts']:,}P" for n, r in enumerate(qa("SELECT * FROM points WHERE guild=? ORDER BY pts DESC LIMIT 15", i.guild_id), 1)) or "없음")
@feat("랭킹", "연속 출석 랭킹", "출석 스트릭 순", [])
async def _(i, a): return emb("🔥 연속 출석", "\n".join(f"`{n}.` {name_of(i.guild, r['user'])} — {r['streak']}일" for n, r in enumerate(qa("SELECT * FROM points WHERE guild=? ORDER BY streak DESC LIMIT 15", i.guild_id), 1)) or "없음")
@feat("랭킹", "주캐별 랭킹", "특정 캐릭터 유저 중 전투력 순", [P("c", "캐릭터")])
async def _(i, a): return emb(f"🎭 {a['c']} 랭킹", "\n".join(f"`{n}.` {fmt_member(i.guild, r)}" for n, r in enumerate(qa("SELECT * FROM members WHERE guild=? AND main=? ORDER BY power DESC LIMIT 15", i.guild_id, a["c"]), 1)) or "없음")
@feat("랭킹", "역할별 랭킹", "특정 역할 멤버 전투력 순", [P("r", "역할", "role")])
async def _(i, a):
    ids = {m.id for m in a["r"].members}
    rows = [r for r in qa("SELECT * FROM members WHERE guild=? ORDER BY power DESC", i.guild_id) if r["user"] in ids][:15]
    return emb(f"{a['r'].name} 랭킹", "\n".join(f"`{n}.` {fmt_member(i.guild, r)}" for n, r in enumerate(rows, 1)) or "없음")
@feat("랭킹", "랭킹 통계 요약", "1위·평균·중앙값", [])
async def _(i, a):
    ps = sorted((r["power"] for r in qa("SELECT power FROM members WHERE guild=? AND power>0", i.guild_id)), reverse=True)
    if not ps: return "기록 없음"
    return f"📊 1위 {ps[0]:,} · 평균 {sum(ps) // len(ps):,} · 중앙값 {ps[len(ps) // 2]:,} · 인원 {len(ps)}"
for _lo, _hi in [(0, 1000), (1000, 3000), (3000, 6000), (6000, 10000), (10000, 20000), (20000, 40000), (40000, 80000), (80000, 10**9)]:
    def _mk(lo=_lo, hi=_hi):
        async def fn(i, a):
            rows = qa("SELECT * FROM members WHERE guild=? AND power>=? AND power<? ORDER BY power DESC", i.guild_id, lo, hi)
            return emb(f"📊 전투력 {lo:,}~{hi:,} 구간 ({len(rows)}명)", "\n".join(fmt_member(i.guild, r) for r in rows[:30]) or "없음")
        return fn
    add_feat("랭킹", f"전투력 구간 {_lo:,}~{('∞' if _hi >= 10**9 else format(_hi, ','))}", "해당 구간 멤버", _mk(), [], False, "구간")

# ───────── 티어 (생성) ─────────
for _t in TIERS:
    _tn, _te, _tp = _t[1], _t[2], _t[0]
    def _mk_list(tn=_tn):
        async def fn(i, a):
            rows = [r for r in qa("SELECT * FROM members WHERE guild=? ORDER BY power DESC", i.guild_id) if tier_of(r["power"])[1] == tn]
            return emb(f"{tier_of(rows[0]['power'])[2] if rows else ''} {tn} 멤버 ({len(rows)})", "\n".join(fmt_member(i.guild, r) for r in rows[:30]) or "없음")
        return fn
    def _mk_cnt(tn=_tn):
        async def fn(i, a): return f"{tn}: {sum(1 for r in qa('SELECT power FROM members WHERE guild=?', i.guild_id) if tier_of(r['power'])[1] == tn)}명"
        return fn
    def _mk_avg(tn=_tn):
        async def fn(i, a):
            ps = [r["power"] for r in qa("SELECT power FROM members WHERE guild=?", i.guild_id) if tier_of(r["power"])[1] == tn]
            return f"{tn} 평균 전투력: {sum(ps) // len(ps):,}" if ps else f"{tn} 멤버 없음"
        return fn
    def _mk_req(tn=_tn, tp=_tp, te=_te):
        async def fn(i, a):
            me = mrow(i.guild_id, i.user.id)["power"]
            return f"{te} **{tn}** 조건: 전투력 {tp:,} 이상\n내 전투력 {me:,} → " + ("✅ 달성" if me >= tp else f"{tp - me:,} 부족")
        return fn
    def _mk_role(tn=_tn):
        async def fn(i, a):
            r = q1("SELECT role FROM tier_roles WHERE guild=? AND tier=?", i.guild_id, tn)
            return f"{tn} 연결 역할: " + (f"<@&{r['role']}>" if r else "없음")
        return fn
    def _mk_give(tn=_tn):
        async def fn(i, a):
            r = q1("SELECT role FROM tier_roles WHERE guild=? AND tier=?", i.guild_id, tn)
            if not r: raise FeatErr("연결된 역할 없음")
            role = i.guild.get_role(r["role"]); n = 0
            for row in qa("SELECT user, power FROM members WHERE guild=?", i.guild_id):
                if tier_of(row["power"])[1] == tn and (m := i.guild.get_member(row["user"])): await m.add_roles(role); n += 1
            return f"✅ {n}명에게 {role.mention} 지급"
        return fn
    add_feat("티어", f"{_tn} 멤버 목록", f"{_te} {_tn} 티어 멤버", _mk_list(), [], False, "tier 티어")
    add_feat("티어", f"{_tn} 인원수", f"{_tn} 티어 인원", _mk_cnt(), [], False, "tier")
    add_feat("티어", f"{_tn} 평균 전투력", f"{_tn} 티어 평균", _mk_avg(), [], False, "tier")
    add_feat("티어", f"{_tn} 승급 조건", f"{_tn} 되려면", _mk_req(), [], False, "tier 승급")
    add_feat("티어", f"{_tn} 연결 역할 보기", f"{_tn} 티어 역할", _mk_role(), [], False, "tier role")
    add_feat("🔒 티어 관리", f"{_tn} 티어 역할 일괄 지급", f"{_tn} 전원에게 연결 역할", _mk_give(), [], A, "tier role")
@feat("티어", "티어표", "티어 기준표", [], False, "tier")
async def _(i, a): return emb("🏆 전투력 티어표", "\n".join(f"{t[2]} **{t[1]}** — {t[0]:,} 이상" for t in TIERS))
@feat("티어", "내 티어", "내 티어와 다음 티어", [])
async def _(i, a): p = mrow(i.guild_id, i.user.id)["power"]; t = tier_of(p); nt = next_tier(p); return f"{t[2]} **{t[1]}** ({p:,})" + (f" → 다음 {nt[1]}까지 {nt[0] - p:,}" if nt else " · 최고 티어!")
@feat("티어", "전투력으로 티어 계산", "숫자 입력 → 티어", [P("n", "전투력", "int", lo=0)])
async def _(i, a): t = tier_of(a["n"]); return f"{a['n']:,} → {t[2]} {t[1]}"

# ───────── 캐릭터 (생성: 16 × 12 + 상성 16×15) ─────────
def char_users(g, c): return qa("SELECT * FROM members WHERE guild=? AND main=? ORDER BY power DESC", g, c)
def matchup(a, b):
    h = int(hashlib.md5(f"{min(a, b)}|{max(a, b)}".encode()).hexdigest(), 16)
    adv = 35 + h % 31  # 35~65
    return adv if a < b else 100 - adv
for _c, _d in CHARS.items():
    def mk(c=_c, d=_d):
        async def info(i, a):
            e = emb(f"🎭 {c}", f"타입 **{d['type']}** · 난이도 **{d['diff']}** · 티어 **{d['tier']}**", 0x9B59B6)
            e.add_field(name="스킬", value="\n".join(f"{n}. {s}" for n, s in enumerate(d["skills"], 1)), inline=False)
            e.add_field(name="카운터", value=d["counter"], inline=False); e.add_field(name="팁", value=d["tip"], inline=False)
            e.set_footer(text=f"클랜 내 주캐 유저 {len(char_users(i.guild_id, c))}명"); return e
        async def skills(i, a): return emb(f"🎯 {c} 스킬", "\n".join(f"**{n}번** {s}" for n, s in enumerate(d["skills"], 1)))
        async def combo1(i, a): return f"🥉 **{c} 초급 콤보**\nM1 ×4 → {d['skills'][0]} → 대시 빠지기"
        async def combo2(i, a): return f"🥈 **{c} 중급 콤보**\nM1 ×3 → {d['skills'][0]} → M1 ×2 → {d['skills'][1]} → 거리 벌리기"
        async def combo3(i, a): return f"🥇 **{c} 고급 콤보**\n{d['skills'][2]} 선제 → M1 ×3 → {d['skills'][0]} 캔슬 → M1 ×4 → {d['skills'][1]} → 벽콤 {d['skills'][3]} 마무리"
        async def counter(i, a): return f"🛡️ **{c} 상대법**\n{d['counter']}\n약점 구간: {d['skills'][3]} 후딜"
        async def tierv(i, a): return f"📊 {c} 티어 평가: **{d['tier']}** ({d['type']}, 난이도 {d['diff']})\n{'메타 캐릭터' if d['tier'] == 'S' else '안정적 픽' if d['tier'] == 'A' else '숙련 시 강력'}"
        async def users(i, a): rows = char_users(i.guild_id, c); return emb(f"👥 {c} 주캐 유저 ({len(rows)})", "\n".join(fmt_member(i.guild, r) for r in rows[:25]) or "없음")
        async def crank(i, a): rows = char_users(i.guild_id, c); return emb(f"🏆 {c} 내 전투력 랭킹", "\n".join(f"`{n}.` {fmt_member(i.guild, r)}" for n, r in enumerate(rows[:15], 1)) or "없음")
        async def tip(i, a): return f"💡 **{c} 팁**: {d['tip']}\n+ {random.choice(TIPS)}"
        async def meme(i, a): return f"😂 {c} 유저 특: {random.choice(['울트 아껴두다 죽음', '콤보 연습만 3시간', '티밍 당하면 바로 서버 호핑', '스킬 쿨 암기 완료', '벽콤 성공하면 채팅에 자랑'])}"
        async def best(i, a):
            ms = sorted(((matchup(c, o), o) for o in CHAR_LIST if o != c), reverse=True)
            return emb(f"⚖️ {c} 상성표", "**유리**: " + ", ".join(f"{o}({p}%)" for p, o in ms[:4]) + "\n**불리**: " + ", ".join(f"{o}({p}%)" for p, o in ms[-4:]))
        return [("정보", "캐릭터 기본 정보", info), ("스킬", "스킬 목록", skills), ("초급 콤보", "입문 콤보", combo1), ("중급 콤보", "중급 콤보", combo2), ("고급 콤보", "고급 콤보", combo3),
                ("상대법", "카운터 방법", counter), ("티어 평가", "현재 메타 평가", tierv), ("주캐 유저", "클랜 내 이 캐릭 유저", users), ("캐릭터 내 랭킹", "이 캐릭 유저 전투력 순", crank),
                ("팁", "플레이 팁", tip), ("밈", "캐릭터 밈", meme), ("상성표", "유리/불리 캐릭", best)]
    for _n, _desc, _fn in mk(): add_feat("캐릭터", f"{_c} {_n}", f"{_c} — {_desc}", _fn, [], False, f"character 캐릭 {_d['type']} {_d['tier']}")
for _a in CHAR_LIST:
    for _b in CHAR_LIST:
        if _a == _b: continue
        def _mk(x=_a, y=_b):
            async def fn(i, a):
                p = matchup(x, y); dx, dy = CHARS[x], CHARS[y]
                verdict = "유리" if p >= 55 else "불리" if p <= 45 else "비등"
                return emb(f"⚔️ {x} vs {y}", f"**{x} 승률 예상 {p}%** ({verdict})\n{x}: {dx['type']} / {y}: {dy['type']}\n핵심: {dy['counter']}\n주의 스킬: {dy['skills'][3]}", 0xE67E22)
            return fn
        add_feat("상성", f"{_a} vs {_b}", f"{_a}로 {_b} 상대할 때 상성", _mk(), [], False, "matchup 상성 vs")
@feat("캐릭터", "캐릭터 목록", "모든 캐릭터", [])
async def _(i, a): return emb("🎭 캐릭터", "\n".join(f"**{c}** — {d['type']} · {d['tier']}" for c, d in CHARS.items()))
@feat("캐릭터", "캐릭터 랜덤 뽑기", "오늘 할 캐릭 추천", [], False, "random")
async def _(i, a): c = random.choice(CHAR_LIST); return f"🎲 오늘의 캐릭터: **{c}** ({CHARS[c]['type']})"
@feat("캐릭터", "상성 계산기", "두 캐릭 이름 입력", [P("x", "내 캐릭"), P("y", "상대 캐릭")])
async def _(i, a):
    if a["x"] not in CHARS or a["y"] not in CHARS: raise FeatErr("캐릭터 이름 확인 (캐릭터 목록 참고)")
    return f"⚔️ {a['x']} vs {a['y']}: {matchup(a['x'], a['y'])}%"
@feat("캐릭터", "티어별 캐릭터", "S/A/B 티어 캐릭", [])
async def _(i, a): return "\n".join(f"**{t}**: " + ", ".join(c for c, d in CHARS.items() if d["tier"] == t) for t in "SAB")
@feat("캐릭터", "난이도별 캐릭터", "쉬움/보통/어려움", [])
async def _(i, a): return "\n".join(f"**{t}**: " + ", ".join(c for c, d in CHARS.items() if d["diff"] == t) for t in ["쉬움", "보통", "어려움"])
@feat("캐릭터", "타입별 캐릭터", "근접/원거리/각성", [])
async def _(i, a):
    g = {}
    for c, d in CHARS.items(): g.setdefault(d["type"].split()[0], []).append(c)
    return "\n".join(f"**{k}**: {', '.join(v)}" for k, v in g.items())
@feat("캐릭터", "스킬 검색", "스킬 이름으로 캐릭 찾기", [P("s", "스킬 이름")])
async def _(i, a): return "\n".join(f"{c}: {s}" for c, d in CHARS.items() for s in d["skills"] if a["s"] in s) or "없음"
@feat("캐릭터", "내 주캐 정보", "내 주캐 상세", [])
async def _(i, a):
    c = mrow(i.guild_id, i.user.id)["main"]
    if c not in CHARS: return f"주캐 미설정 또는 데이터 없음 ({c})"
    d = CHARS[c]; return emb(f"🎭 {c}", f"{d['type']} · {d['diff']} · {d['tier']}\n스킬: {', '.join(d['skills'])}\n팁: {d['tip']}")

# ───────── 포인트 / 상점 ─────────
@feat("포인트", "출석 체크", "매일 +100P (연속 보너스)", [], False, "daily 출석")
async def _(i, a): return await do_daily(i)
@feat("포인트", "내 포인트", "보유 포인트", [], False, "points")
async def _(i, a): return f"💰 {prow(i.guild_id, i.user.id)['pts']:,}P"
@feat("포인트", "멤버 포인트 조회", "다른 멤버 포인트", [PM])
async def _(i, a): return f"💰 {a['m'].display_name}: {prow(i.guild_id, a['m'].id)['pts']:,}P"
@feat("포인트", "포인트 송금", "포인트 보내기", [PM, P("n", "금액", "int", lo=1)], False, "pay")
async def _(i, a):
    if prow(i.guild_id, i.user.id)["pts"] < a["n"]: raise FeatErr("포인트 부족")
    add_pts(i.guild_id, i.user.id, -a["n"]); add_pts(i.guild_id, a["m"].id, a["n"]); return f"💸 {a['m'].mention} 에게 {a['n']:,}P 송금"
def gamble(mult, prob):
    async def fn(i, a):
        p = prow(i.guild_id, i.user.id)
        if p["pts"] < a["n"]: raise FeatErr("포인트 부족")
        if random.random() < prob: t = add_pts(i.guild_id, i.user.id, a["n"] * (mult - 1)); return f"🎰 성공! +{a['n'] * (mult - 1):,}P (보유 {t:,}P)"
        t = add_pts(i.guild_id, i.user.id, -a["n"]); return f"💸 실패… -{a['n']:,}P (보유 {t:,}P)"
    return fn
for _m, _p in [(2, 0.5), (3, 0.33), (5, 0.2), (10, 0.1), (50, 0.02)]:
    add_feat("포인트", f"도박 ×{_m}", f"확률 {int(_p * 100)}%로 {_m}배", gamble(_m, _p), [P("n", "금액", "int", lo=10, hi=1_000_000)], False, "gamble 도박")
@feat("포인트", "올인", "전 재산 50% 도박", [])
async def _(i, a):
    p = prow(i.guild_id, i.user.id)["pts"]
    if p < 10: raise FeatErr("10P 이상 필요")
    if random.random() < 0.5: return f"🎰 올인 성공! {add_pts(i.guild_id, i.user.id, p):,}P"
    add_pts(i.guild_id, i.user.id, -p); return "💀 올인 실패… 0P"
@feat("포인트", "복권 (100P)", "1/100 확률 5000P", [])
async def _(i, a):
    if prow(i.guild_id, i.user.id)["pts"] < 100: raise FeatErr("100P 필요")
    add_pts(i.guild_id, i.user.id, -100); n = random.randint(1, 100)
    if n == 7: add_pts(i.guild_id, i.user.id, 5000); return "🎉 복권 당첨! +5000P"
    if n % 10 == 7: add_pts(i.guild_id, i.user.id, 200); return "🎊 소액 당첨 +200P"
    return f"꽝 ({n})"
@feat("포인트", "슬롯머신 (50P)", "777 잭팟", [])
async def _(i, a):
    if prow(i.guild_id, i.user.id)["pts"] < 50: raise FeatErr("50P 필요")
    add_pts(i.guild_id, i.user.id, -50); s = [random.choice("🍒🍋🔔⭐7️⃣") for _ in range(3)]
    win = 2000 if s == ["7️⃣"] * 3 else 300 if len(set(s)) == 1 else 60 if len(set(s)) == 2 else 0
    if win: add_pts(i.guild_id, i.user.id, win)
    return f"🎰 {' '.join(s)} → {'+' + str(win) + 'P' if win else '꽝'}"
@feat("포인트", "주사위 대결 (베팅)", "봇과 주사위 높은 쪽 승", [P("n", "금액", "int", lo=10)])
async def _(i, a):
    if prow(i.guild_id, i.user.id)["pts"] < a["n"]: raise FeatErr("포인트 부족")
    u, b = random.randint(1, 6), random.randint(1, 6)
    if u > b: add_pts(i.guild_id, i.user.id, a["n"]); return f"🎲 {u} vs {b} 승리! +{a['n']}P"
    if u < b: add_pts(i.guild_id, i.user.id, -a["n"]); return f"🎲 {u} vs {b} 패배 -{a['n']}P"
    return f"🎲 {u} vs {b} 무승부"
@feat("포인트", "홀짝 (베팅)", "홀/짝 맞추기 2배", [P("c", "홀/짝", "choice", choices=["홀", "짝"]), P("n", "금액", "int", lo=10)])
async def _(i, a):
    if prow(i.guild_id, i.user.id)["pts"] < a["n"]: raise FeatErr("포인트 부족")
    r = random.randint(1, 10); win = (r % 2 == 1) == (a["c"] == "홀")
    add_pts(i.guild_id, i.user.id, a["n"] if win else -a["n"]); return f"{r} → {'홀' if r % 2 else '짝'} {'🎉 승리' if win else '💸 패배'}"
@feat("포인트", "블랙잭 (간이)", "21에 가까운 쪽 승", [P("n", "금액", "int", lo=10)])
async def _(i, a):
    if prow(i.guild_id, i.user.id)["pts"] < a["n"]: raise FeatErr("포인트 부족")
    draw = lambda: sum(random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 11]) for _ in range(2))
    u, b = draw(), draw()
    while u < 17: u += random.randint(1, 10)
    while b < 17: b += random.randint(1, 10)
    win = (u <= 21) and (b > 21 or u > b)
    add_pts(i.guild_id, i.user.id, a["n"] if win else -a["n"]); return f"🃏 나 {u} vs 딜러 {b} → {'승리 +' if win else '패배 -'}{a['n']}P"
for _n in (100, 500, 1000, 5000):
    for _s in (1, -1):
        def _mk(n=_n, s=_s):
            async def fn(i, a): t = add_pts(i.guild_id, a["m"].id, s * n); return f"✅ {a['m'].mention} {s * n:+,}P (보유 {t:,})"
            return fn
        add_feat("🔒 포인트 관리", f"포인트 {'+' if _s > 0 else '-'}{_n:,}", "포인트 프리셋", _mk(), [PM], A, "points")
@feat("🔒 포인트 관리", "포인트 지급/차감", "임의 금액", [PM, P("n", "금액(음수 가능)", "int")], A)
async def _(i, a): return f"✅ 보유 {add_pts(i.guild_id, a['m'].id, a['n']):,}P"
@feat("🔒 포인트 관리", "포인트 설정", "포인트 직접 설정", [PM, P("n", "값", "int", lo=0)], A)
async def _(i, a): prow(i.guild_id, a["m"].id); ex("UPDATE points SET pts=? WHERE guild=? AND user=?", a["n"], i.guild_id, a["m"].id); return "✅"
@feat("🔒 포인트 관리", "포인트 전원 지급", "모든 멤버 +N", [P("n", "금액", "int")], A)
async def _(i, a):
    for m in i.guild.members:
        if not m.bot: add_pts(i.guild_id, m.id, a["n"])
    return "✅"
@feat("🔒 포인트 관리", "포인트 전원 초기화", "모두 0P", [], A)
async def _(i, a): ex("UPDATE points SET pts=0 WHERE guild=?", i.guild_id); return "✅"
@feat("🔒 포인트 관리", "역할 전원 포인트", "역할 멤버 +N", [P("r", "역할", "role"), P("n", "금액", "int")], A)
async def _(i, a):
    for m in a["r"].members: add_pts(i.guild_id, m.id, a["n"])
    return f"✅ {len(a['r'].members)}명"
@feat("🔒 포인트 관리", "출석 초기화", "멤버 출석/스트릭 초기화", [PM], A)
async def _(i, a): ex("UPDATE points SET last_daily=0, streak=0 WHERE guild=? AND user=?", i.guild_id, a["m"].id); return "✅"
@feat("상점", "상점 목록", "포인트로 살 수 있는 아이템", [], False, "shop")
async def _(i, a): return emb("🛒 상점", "\n".join(f"**{n}** — {p:,}P · {d}" for n, p, d in SHOP))
@feat("상점", "내 인벤토리", "보유 아이템", [], False, "inventory")
async def _(i, a): return "🎒 " + (", ".join(f"{r['item']}×{r['qty']}" for r in qa("SELECT * FROM inventory WHERE guild=? AND user=? AND qty>0", i.guild_id, i.user.id)) or "비어있음")
for _name, _price, _desc in SHOP:
    def _buy(n=_name, p=_price):
        async def fn(i, a):
            if prow(i.guild_id, i.user.id)["pts"] < p: raise FeatErr(f"{p}P 필요")
            add_pts(i.guild_id, i.user.id, -p); ex("INSERT INTO inventory VALUES(?,?,?,1) ON CONFLICT(guild,user,item) DO UPDATE SET qty=qty+1", i.guild_id, i.user.id, n)
            return f"🛍️ **{n}** 구매! (-{p}P)"
        return fn
    def _info(n=_name, p=_price, d=_desc):
        async def fn(i, a): return f"🛒 **{n}** — {p:,}P\n{d}\n보유: {(q1('SELECT qty FROM inventory WHERE guild=? AND user=? AND item=?', i.guild_id, i.user.id, n) or {'qty': 0})['qty']}개"
        return fn
    def _use(n=_name):
        async def fn(i, a):
            r = q1("SELECT qty FROM inventory WHERE guild=? AND user=? AND item=?", i.guild_id, i.user.id, n)
            if not r or r["qty"] < 1: raise FeatErr("보유하지 않음")
            ex("UPDATE inventory SET qty=qty-1 WHERE guild=? AND user=? AND item=?", i.guild_id, i.user.id, n)
            await log(i.guild, emb("🎁 아이템 사용", f"{i.user.mention} — {n}", 0x2ECC71)); return f"✅ **{n}** 사용! 관리자에게 알림이 갔어요."
        return fn
    add_feat("상점", f"구매: {_name}", f"{_price:,}P — {_desc}", _buy(), [], False, "shop buy")
    add_feat("상점", f"아이템 정보: {_name}", _desc, _info(), [], False, "shop")
    add_feat("상점", f"사용: {_name}", f"{_name} 1개 사용 (관리자 알림)", _use(), [], False, "shop use")
@feat("🔒 포인트 관리", "아이템 지급", "멤버에게 아이템", [PM, P("t", "아이템 이름"), P("n", "개수", "int", False, lo=1)], A)
async def _(i, a): ex("INSERT INTO inventory VALUES(?,?,?,?) ON CONFLICT(guild,user,item) DO UPDATE SET qty=qty+excluded.qty", i.guild_id, a["m"].id, a["t"], a["n"] or 1); return "✅"
@feat("🔒 포인트 관리", "인벤토리 초기화", "멤버 아이템 전부 삭제", [PM], A)
async def _(i, a): ex("DELETE FROM inventory WHERE guild=? AND user=?", i.guild_id, a["m"].id); return "✅"

# ───────── 재미 ─────────
for _f in (2, 4, 6, 8, 10, 12, 20, 100):
    def _mk(f=_f):
        async def fn(i, a): n = a["n"] or 1; rolls = [random.randint(1, f) for _ in range(min(n, 20))]; return f"🎲 d{f}: {' + '.join(map(str, rolls))}" + (f" = **{sum(rolls)}**" if n > 1 else "")
        return fn
    add_feat("재미", f"주사위 d{_f}", f"{_f}면 주사위 (개수 선택)", _mk(), [P("n", "개수", "int", False, lo=1, hi=20)], False, "dice")
@feat("재미", "동전 던지기", "앞/뒤", [], False, "coin")
async def _(i, a): return f"🪙 **{random.choice(['앞면', '뒷면'])}**"
@feat("재미", "동전 10번", "앞면 몇 번?", [])
async def _(i, a): r = [random.choice("앞뒤") for _ in range(10)]; return f"🪙 {''.join(r)} → 앞 {r.count('앞')} / 뒤 {r.count('뒤')}"
@feat("재미", "가위바위보", "봇과 대결 (승리 +20P)", [P("c", "가위/바위/보", "choice", choices=["가위", "바위", "보"])], False, "rps")
async def _(i, a):
    b = random.choice(["가위", "바위", "보"]); u = a["c"]; win = {("가위", "보"), ("바위", "가위"), ("보", "바위")}
    if u == b: return f"✊ {u} vs {b} 무승부"
    if (u, b) in win: add_pts(i.guild_id, i.user.id, 20); return f"✊ {u} vs {b} 🎉 승리 +20P"
    return f"✊ {u} vs {b} 😭 패배"
for _k in ["가위", "바위", "보"]:
    def _mk(u=_k):
        async def fn(i, a):
            b = random.choice(["가위", "바위", "보"]); win = {("가위", "보"), ("바위", "가위"), ("보", "바위")}
            if u == b: return f"✊ {u} vs {b} 무승부"
            if (u, b) in win: add_pts(i.guild_id, i.user.id, 20); return f"✊ {u} vs {b} 🎉 승리 +20P"
            return f"✊ {u} vs {b} 😭 패배"
        return fn
    add_feat("재미", f"가위바위보: {_k}", f"{_k} 내기", _mk(), [], False, "rps")
@feat("재미", "8볼", "마법의 8번 공", [P("q", "질문")], False, "8ball")
async def _(i, a): return f"🎱 {a['q']}\n→ **{random.choice(['확실히 그렇다', '그렇다', '아마도', '다시 물어봐', '글쎄…', '아니다', '절대 아니다', '사이타마에게 물어봐', '가로우도 모름'])}**"
@feat("재미", "룰렛", "쉼표 항목 중 하나", [P("l", "항목들", "list")], False, "roulette pick")
async def _(i, a):
    if len(a["l"]) < 2: raise FeatErr("2개 이상")
    return f"🎯 **{random.choice(a['l'])}**"
@feat("재미", "항목 섞기", "쉼표 항목 순서 섞기", [P("l", "항목들", "list")], False, "shuffle")
async def _(i, a): l = a["l"][:]; random.shuffle(l); return " → ".join(l)
for _k in (1, 2, 3, 5):
    def _mk(k=_k):
        async def fn(i, a):
            if len(a["l"]) < k: raise FeatErr(f"{k}개 이상 필요")
            return f"🎉 당첨: {', '.join(random.sample(a['l'], k))}"
        return fn
    add_feat("재미", f"추첨 {_k}명", f"항목 중 {_k}개 랜덤", _mk(), [P("l", "항목들", "list")], False, "draw 추첨")
for _k in (2, 3, 4, 5):
    def _mk(k=_k):
        async def fn(i, a):
            l = a["l"][:]; random.shuffle(l); teams = [l[j::k] for j in range(k)]
            return "\n".join(f"**{j + 1}팀**: {', '.join(t)}" for j, t in enumerate(teams))
        return fn
    add_feat("재미", f"{_k}팀 나누기", f"항목을 {_k}팀으로", _mk(), [P("l", "이름들", "list")], False, "team split")
@feat("재미", "음성 채널 팀 나누기", "내 음성 채널 인원을 2팀으로", [])
async def _(i, a):
    vc = i.user.voice and i.user.voice.channel
    if not vc: raise FeatErr("음성 채널에 먼저 들어가세요")
    l = [m.display_name for m in vc.members]; random.shuffle(l); return f"**A팀**: {', '.join(l[::2])}\n**B팀**: {', '.join(l[1::2])}"
FORTUNES = {"오늘의 운세": ["대박", "길", "보통", "흉", "대흉"], "전투 운세": ["연승 예감", "콤보가 잘 들어감", "평범", "티밍 조심", "오늘은 쉬어"],
            "티밍 운세": ["평화로움", "1번 당함", "2번 당함", "집중 타겟", "서버 옮겨"], "포인트 운세": ["도박 대박", "소소한 이득", "본전", "손실", "올인 금지"],
            "클랜 운세": ["새 클랜원 등장", "클랜전 승리", "평화", "내부 갈등 조심", "휴식일"], "연습 운세": ["새 콤보 터득", "실력 상승", "현상 유지", "슬럼프", "휴식 필요"]}
for _fn_name, _opts in FORTUNES.items():
    def _mk(name=_fn_name, opts=_opts):
        async def fn(i, a):
            rnd = random.Random(f"{i.user.id}{datetime.date.today()}{name}")
            return f"🔮 **{i.user.display_name}의 {name}**\n결과: **{rnd.choice(opts)}** · 운 지수 {rnd.randint(1, 100)}/100\n행운의 캐릭: {rnd.choice(CHAR_LIST)} · 한마디: {rnd.choice(TIPS)}"
        return fn
    add_feat("재미", _fn_name, f"오늘의 {_fn_name} (하루 고정)", _mk(), [], False, "fortune 운세")
@feat("재미", "전투력 스카우터", "(장난) 랜덤 전투력 측정", [P("m", "멤버", "member", False)], False, "scouter")
async def _(i, a): m = a["m"] or i.user; v = random.randint(5, 999999); return f"🔭 **{m.display_name}** 전투력… **{v:,}**!! {'💥 스카우터 폭발!' if v > 900000 else ''}"
@feat("재미", "가상 대결", "두 멤버 가상 1v1 (실전투력 반영)", [P("m", "상대", "member")], False, "duel")
async def _(i, a):
    pa, pb = mrow(i.guild_id, i.user.id)["power"] + 500, mrow(i.guild_id, a["m"].id)["power"] + 500
    w = i.user if random.random() < pa / (pa + pb) else a["m"]
    mv = ["연속 펀치", "진심 펀치", "소닉 스텝", "유수암쇄권", "아토믹 슬래시", "풀스윙", "사이코 쓰나미"]
    return f"⚔️ {i.user.display_name} vs {a['m'].display_name}\n{random.choice(mv)}! … {random.choice(mv)}!!\n🏆 승자: **{w.display_name}**"
@feat("재미", "랜덤 멤버 대결", "랜덤 두 클랜원 가상 대결", [])
async def _(i, a):
    rows = qa("SELECT user, power FROM members WHERE guild=? AND power>0", i.guild_id)
    if len(rows) < 2: raise FeatErr("클랜원 부족")
    x, y = random.sample(rows, 2); w = x if random.random() < (x["power"] + 1) / (x["power"] + y["power"] + 2) else y
    return f"⚔️ {name_of(i.guild, x['user'])} vs {name_of(i.guild, y['user'])} → 🏆 {name_of(i.guild, w['user'])}"
@feat("재미", "칭찬하기", "랜덤 칭찬 (본인만 봄)", [PM], False, "praise")
async def _(i, a): return f"💖 {a['m'].display_name}: {random.choice(['콤보가 예술', '진심 펀치급 존재감', '클랜의 에이스', '오늘도 캐리', '가로우도 피하는 실력', 'S급 히어로'])}!"
@feat("재미", "칭찬 공개로 보내기", "채널에 칭찬 메시지 공개", [PM])
async def _(i, a): await i.channel.send(f"💖 {a['m'].mention} {random.choice(['콤보가 예술이다', '클랜의 에이스', '오늘도 캐리 담당', 'S급 히어로 그 자체'])}! (by {i.user.display_name})"); return "✅ 전송"
@feat("재미", "밈", "랜덤 가강전 밈", [], False, "meme")
async def _(i, a): return f"😂 {random.choice(MEMES)}"
@feat("재미", "명언", "랜덤 전투 명언", [], False, "quote")
async def _(i, a): return f"📜 {random.choice(QUOTES)}"
for _n, _q in enumerate(QUOTES, 1):
    def _mk(q=_q):
        async def fn(i, a): return f"📜 {q}"
        return fn
    add_feat("명언", f"명언 #{_n}", _q[:60], _mk(), [], False, "quote")
for _n, _m in enumerate(MEMES, 1):
    def _mk(m=_m):
        async def fn(i, a): return f"😂 {m}"
        return fn
    add_feat("밈", f"밈 #{_n}", _m[:60], _mk(), [], False, "meme")
for _n, _t in enumerate(TIPS, 1):
    def _mk(t=_t):
        async def fn(i, a): return f"💡 {t}"
        return fn
    add_feat("팁", f"팁 #{_n}", _t[:60], _mk(), [], False, "tip")
@feat("재미", "오늘의 팁", "랜덤 팁", [])
async def _(i, a): return f"💡 {random.choice(TIPS)}"
@feat("재미", "투표 만들기 (공개)", "채널에 이모지 투표 게시", [P("q", "질문"), P("l", "선택지", "list")], False, "poll")
async def _(i, a):
    opts = a["l"][:10]; nums = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    if len(opts) < 2: raise FeatErr("선택지 2개 이상")
    m = await i.channel.send(embed=emb(f"🗳️ {a['q']}", "\n".join(f"{nums[k]} {o}" for k, o in enumerate(opts)), 0x3498DB))
    for k in range(len(opts)): await m.add_reaction(nums[k])
    return "✅ 투표 게시"
@feat("재미", "찬반 투표 (공개)", "👍👎 투표", [P("q", "질문")])
async def _(i, a): m = await i.channel.send(embed=emb(f"🗳️ {a['q']}", "👍 찬성 / 👎 반대")); await m.add_reaction("👍"); await m.add_reaction("👎"); return "✅"
@feat("재미", "같이하자 (공개)", "같이 할 사람 모집 게시", [P("n", "인원", "int", False, lo=1, hi=20), P("t", "메모", required=False)], False, "lfg")
async def _(i, a): m = await i.channel.send(embed=emb("🎮 같이 할 사람!", f"{i.user.mention} 님이 **{a['n'] or 3}명** 모집\n{a['t'] or ''}", 0x3498DB)); await m.add_reaction("✋"); return "✅"
@feat("재미", "숫자 맞추기", "1~100 추측 (힌트 제공)", [P("n", "내 추측", "int", lo=1, hi=100)], False, "guess")
async def _(i, a):
    ans = random.Random(f"{i.user.id}{datetime.date.today()}guess").randint(1, 100)
    if a["n"] == ans: add_pts(i.guild_id, i.user.id, 50); return f"🎉 정답 {ans}! +50P (오늘의 정답은 하루 동안 같아요)"
    return "⬆️ 더 큼" if a["n"] < ans else "⬇️ 더 작음"
for _lo, _hi in [(1, 10), (1, 50), (1, 1000)]:
    def _mk(lo=_lo, hi=_hi):
        async def fn(i, a):
            ans = random.Random(f"{i.user.id}{datetime.date.today()}g{hi}").randint(lo, hi)
            if a["n"] == ans: add_pts(i.guild_id, i.user.id, 30); return f"🎉 정답 {ans}! +30P"
            return "⬆️ 더 큼" if a["n"] < ans else "⬇️ 더 작음"
        return fn
    add_feat("재미", f"숫자 맞추기 {_lo}~{_hi}", "오늘의 숫자 추측", _mk(), [P("n", "추측", "int", lo=_lo, hi=_hi)], False, "guess")
for _n, (_q, _ans) in enumerate(QUIZ, 1):
    def _mk(q=_q, ans=_ans):
        async def fn(i, a):
            if a["x"].strip().lower().replace(" ", "") == ans.lower().replace(" ", ""): add_pts(i.guild_id, i.user.id, 15); return f"✅ 정답! **{ans}** (+15P)"
            return f"❌ 오답. 정답은 **{ans}**"
        return fn
    add_feat("퀴즈", f"퀴즈 #{_n}: {_q[:30]}", _q, _mk(), [P("x", _q[:45])], False, "quiz")
@feat("퀴즈", "랜덤 퀴즈 번호", "오늘 풀 퀴즈 추천", [])
async def _(i, a): return f"📝 퀴즈 #{random.randint(1, len(QUIZ))} 을 검색해서 풀어보세요!"
@feat("재미", "타자 연습 문장", "랜덤 문장", [])
async def _(i, a): return f"⌨️ `{random.choice(QUOTES + TIPS)}`"
@feat("재미", "오늘의 캐릭터", "오늘 고정 추천 캐릭", [])
async def _(i, a): return f"🎭 오늘의 캐릭터: **{random.Random(f'{i.user.id}{datetime.date.today()}c').choice(CHAR_LIST)}**"
@feat("재미", "닉네임 생성기", "가강전풍 닉 추천", [])
async def _(i, a): return "✨ " + " / ".join(random.choice(["진심", "무적", "섬광", "폭풍", "침묵", "광기", "심연", "불꽃"]) + random.choice(["펀처", "슬래셔", "스텝퍼", "헌터", "히어로", "사무라이", "배트", "마스터"]) + str(random.randint(1, 99)) for _ in range(3))
@feat("재미", "클랜 이름 생성기", "클랜명 추천", [])
async def _(i, a): return "🏰 " + " / ".join(random.choice(["진심", "최강", "영웅", "괴인", "섬광", "무한"]) + random.choice(["연합", "협회", "길드", "군단", "클럽", "전선"]) for _ in range(3))
@feat("재미", "필살기 이름 생성기", "나만의 필살기", [])
async def _(i, a): return "💥 " + random.choice(["진심", "초고속", "무음", "파멸", "천공", "지옥"]) + " " + random.choice(["연속", "회전", "낙하", "돌진", "폭발"]) + " " + random.choice(["펀치", "참격", "발차기", "포격", "염동파"])
@feat("재미", "랜덤 조합 (캐릭+룰)", "오늘의 제약 플레이", [])
async def _(i, a): return f"🎲 **{random.choice(CHAR_LIST)}** 으로 **{random.choice(['울트 금지', 'M1만 사용', '대시 금지', '가드 금지', '1번 스킬만', '벽콤 금지', '첫 킬까지 도망만'])}** 도전!"
@feat("재미", "랜덤 숫자", "범위 지정 랜덤", [P("lo", "최소", "int"), P("hi", "최대", "int")], False, "random")
async def _(i, a):
    if a["lo"] > a["hi"]: raise FeatErr("최소 ≤ 최대")
    return f"🎲 {random.randint(a['lo'], a['hi'])}"
@feat("재미", "로또 번호", "1~45 중 6개", [], False, "lotto")
async def _(i, a): return "🎱 " + " ".join(map(str, sorted(random.sample(range(1, 46), 6))))
@feat("재미", "빙고판 생성", "5×5 랜덤 숫자", [])
async def _(i, a): n = random.sample(range(1, 26), 25); return "```\n" + "\n".join(" ".join(f"{x:>2}" for x in n[r * 5:(r + 1) * 5]) for r in range(5)) + "\n```"
@feat("재미", "랜덤 이모지", "이모지 하나", [])
async def _(i, a): return random.choice("😀😎🤖👻🎃🔥⚡💎🎯🏆🎮⚔️🛡️👑💀🌟🍀🎲🎰🥊")
@feat("재미", "랜덤 색상", "HEX 색상", [], False, "color")
async def _(i, a): c = random.randint(0, 0xFFFFFF); return emb(f"🎨 #{c:06X}", color=c)
@feat("재미", "사랑 궁합 (장난)", "두 멤버 궁합", [P("m", "멤버1", "member"), P("m2", "멤버2", "member")])
async def _(i, a): v = random.Random(f"{min(a['m'].id, a['m2'].id)}{max(a['m'].id, a['m2'].id)}").randint(0, 100); return f"💞 {a['m'].display_name} ❤ {a['m2'].display_name}: **{v}%**"
@feat("재미", "팀워크 궁합", "두 멤버 듀오 궁합", [P("m", "멤버1", "member"), P("m2", "멤버2", "member")])
async def _(i, a): v = random.Random(f"tw{min(a['m'].id, a['m2'].id)}{max(a['m'].id, a['m2'].id)}").randint(0, 100); return f"🤝 듀오 궁합 **{v}%** — {'완벽한 듀오' if v > 80 else '괜찮음' if v > 50 else '연습 필요'}"
@feat("재미", "오늘 플레이 추천", "캐릭+시간+목표", [])
async def _(i, a): return f"📋 캐릭 **{random.choice(CHAR_LIST)}** · {random.choice([30, 60, 90])}분 · 목표 {random.choice(['5킬', '벽콤 3회 성공', '무패 3판', '새 콤보 1개', '티밍 1회 격퇴'])}"
@feat("재미", "리액션 테스트", "반응속도 (버튼)", [])
async def _(i, a):
    v = discord.ui.View(timeout=30); t0 = time.monotonic() + random.uniform(1.5, 4)
    b = discord.ui.Button(label="기다려…", style=discord.ButtonStyle.secondary, disabled=True); v.add_item(b)
    async def cb(it):
        ms = int((time.monotonic() - t0) * 1000); await it.response.edit_message(content=f"⚡ 반응속도 **{ms}ms** {'🔥' if ms < 250 else ''}", view=None)
    b.callback = cb
    async def go(msg):
        await asyncio.sleep(t0 - time.monotonic()); b.disabled = False; b.label = "지금 클릭!"; b.style = discord.ButtonStyle.success
        try: await msg.edit(view=v)
        except discord.HTTPException: pass
    await i.response.send_message("초록색이 되면 클릭!", view=v, ephemeral=True); asyncio.create_task(go(await i.original_response()))

# ───────── 유틸 ─────────
@feat("유틸", "핑", "봇 지연시간", [], False, "ping")
async def _(i, a): return f"🏓 {round(bot.latency * 1000)}ms"
@feat("유틸", "봇 정보", "업타임·서버 수·기능 수", [], False, "botinfo")
async def _(i, a): return emb("🤖 봇 정보", f"서버 {len(bot.guilds)}개 · 기능 {len(FEATURES):,}개 · 업타임 <t:{START_TS}:R> 부터 · discord.py {discord.__version__}")
@feat("유틸", "타이머", "N초 후 알림 (DM)", [P("n", "초", "int", lo=1, hi=86400), P("t", "메모", required=False)], False, "timer")
async def _(i, a):
    async def go():
        await asyncio.sleep(a["n"])
        try: await i.user.send(f"⏰ 타이머 종료! {a['t'] or ''}")
        except discord.Forbidden: await i.channel.send(f"⏰ {i.user.mention} {a['t'] or '타이머 종료!'}")
    asyncio.create_task(go()); return f"⏳ {a['n']}초 타이머 시작 (DM으로 알림)"
for _s, _lab in [(10, "10초"), (30, "30초"), (60, "1분"), (180, "3분"), (300, "5분"), (600, "10분"), (900, "15분"), (1800, "30분"), (3600, "1시간")]:
    def _mk(s=_s, lab=_lab):
        async def fn(i, a):
            async def go():
                await asyncio.sleep(s)
                try: await i.user.send(f"⏰ {lab} 타이머 종료!")
                except discord.Forbidden: await i.channel.send(f"⏰ {i.user.mention} {lab} 타이머 종료!")
            asyncio.create_task(go()); return f"⏳ {lab} 타이머 시작"
        return fn
    add_feat("유틸", f"타이머 {_lab}", f"{_lab} 뒤 DM 알림", _mk(), [], False, "timer")
@feat("유틸", "리마인더 (분)", "N분 후 메모 DM", [P("n", "분", "int", lo=1, hi=10080), P("t", "내용")], False, "remind")
async def _(i, a):
    async def go():
        await asyncio.sleep(a["n"] * 60)
        try: await i.user.send(f"🔔 리마인더: {a['t']}")
        except discord.Forbidden: pass
    asyncio.create_task(go()); return f"🔔 {a['n']}분 후 알림"
@feat("유틸", "게임 링크", "가강전 바로가기", [], False, "link")
async def _(i, a): return f"🎮 {GAME_LINK}"
@feat("유틸", "서버 직행 링크 보기", "설정된 기본 링크", [])
async def _(i, a): return cfg(i.guild_id)["invite"] or GAME_LINK
@feat("유틸", "티밍 호출", "클랜원 긴급 소집 (공개)", [P("u", "서버 링크", required=False), P("t", "상황", required=False)], False, "teaming sos")
async def _(i, a): await send_teaming(i, a["u"], a["t"] or "티밍 당하는 중!")
@feat("유틸", "메시지 링크 만들기", "메시지 ID → 링크", [P("id", "메시지 ID")])
async def _(i, a): return f"https://discord.com/channels/{i.guild_id}/{i.channel_id}/{a['id']}"
@feat("유틸", "건의하기", "관리자에게 건의 전달", [P("t", "내용", "str")], False, "suggest")
async def _(i, a): await log(i.guild, emb("💡 건의", f"{i.user.mention}: {a['t']}", 0x3498DB)); return "✅ 전달 완료"
@feat("유틸", "신고하기", "멤버 신고 (관리자에게만 전달)", [PM, P("t", "사유", "str")], False, "report")
async def _(i, a): await log(i.guild, emb("🚨 신고", f"신고자 {i.user.mention} → {a['m'].mention}\n{a['t']}", 0xE74C3C)); return "✅ 신고 접수"
@feat("유틸", "티밍 신고", "티밍한 로블록스 유저 기록", [P("r", "로블록스 닉"), P("t", "상황", required=False)])
async def _(i, a): await log(i.guild, emb("⚠️ 티밍 신고", f"{i.user.mention}: `{a['r']}` {a['t'] or ''}", 0xE67E22)); return "✅ 기록됨"
@feat("유틸", "AFK 설정", "닉에 [AFK] 표시", [])
async def _(i, a):
    try: await i.user.edit(nick=f"[AFK] {i.user.display_name}"[:32])
    except discord.Forbidden: raise FeatErr("닉 변경 권한 없음")
    return "💤 AFK"
@feat("유틸", "AFK 해제", "[AFK] 제거", [])
async def _(i, a):
    try: await i.user.edit(nick=i.user.display_name.replace("[AFK] ", ""))
    except discord.Forbidden: raise FeatErr("권한 없음")
    return "✅"
@feat("유틸", "내 소개 수정 요청", "프로필 소개 변경 요청", [P("t", "소개", "str")])
async def _(i, a): await log(i.guild, emb("✏️ 소개 변경 요청", f"{i.user.mention}: {a['t']}", 0x3498DB)); return "✅ 요청 전달"

# ───────── 정보 ─────────
@feat("정보", "유저 정보", "멤버 상세", [P("m", "멤버", "member", False)], False, "userinfo whois")
async def _(i, a):
    m = a["m"] or i.user; e = emb(f"👤 {m}", color=m.color.value or 0x5865F2); e.set_thumbnail(url=m.display_avatar.url)
    e.add_field(name="ID", value=m.id); e.add_field(name="계정 생성", value=f"<t:{int(m.created_at.timestamp())}:D>")
    e.add_field(name="서버 입장", value=f"<t:{int(m.joined_at.timestamp())}:D>" if m.joined_at else "?"); e.add_field(name="역할", value=" ".join(r.mention for r in m.roles[1:][:15]) or "없음", inline=False)
    return e
@feat("정보", "아바타", "프로필 사진", [P("m", "멤버", "member", False)], False, "avatar")
async def _(i, a): m = a["m"] or i.user; e = emb(f"🖼️ {m.display_name}"); e.set_image(url=m.display_avatar.url); return e
@feat("정보", "배너", "프로필 배너", [P("m", "멤버", "member", False)])
async def _(i, a):
    u = await bot.fetch_user((a["m"] or i.user).id)
    if not u.banner: return "배너 없음"
    e = emb("배너"); e.set_image(url=u.banner.url); return e
@feat("정보", "계정 나이", "계정 생성 후 며칠", [P("m", "멤버", "member", False)])
async def _(i, a): m = a["m"] or i.user; return f"📅 {(datetime.datetime.now(datetime.timezone.utc) - m.created_at).days}일"
@feat("정보", "서버 입장 순서", "몇 번째 멤버?", [P("m", "멤버", "member", False)])
async def _(i, a): m = a["m"] or i.user; ms = sorted(i.guild.members, key=lambda x: x.joined_at or datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)); return f"#{ms.index(m) + 1} / {len(ms)}"
@feat("정보", "내 역할", "내 역할 목록", [])
async def _(i, a): return " ".join(r.mention for r in i.user.roles[1:]) or "없음"
@feat("정보", "내 권한", "내 서버 권한", [])
async def _(i, a): return ", ".join(n for n, v in i.user.guild_permissions if v)[:1900]
@feat("정보", "내 ID", "디스코드 ID", [])
async def _(i, a): return f"`{i.user.id}`"
@feat("정보", "상태 확인", "멤버 온라인 상태", [P("m", "멤버", "member", False)])
async def _(i, a): m = a["m"] or i.user; return f"{m.display_name}: {m.status} / 모바일 {m.is_on_mobile()}"
@feat("정보", "활동 확인", "멤버 현재 활동", [P("m", "멤버", "member", False)])
async def _(i, a): m = a["m"] or i.user; return ", ".join(str(x.name) for x in m.activities) or "활동 없음"
@feat("정보", "부스트 정보", "부스트 여부", [P("m", "멤버", "member", False)])
async def _(i, a): m = a["m"] or i.user; return f"💜 <t:{int(m.premium_since.timestamp())}:D> 부터" if m.premium_since else "부스트 안 함"
@feat("정보", "서버 정보", "서버 상세", [], False, "serverinfo")
async def _(i, a):
    g = i.guild; e = emb(f"🏰 {g.name}")
    if g.icon: e.set_thumbnail(url=g.icon.url)
    for k, v in [("멤버", g.member_count), ("채널", len(g.channels)), ("역할", len(g.roles)), ("이모지", len(g.emojis)), ("부스트", f"Lv{g.premium_tier} ({g.premium_subscription_count})"), ("오너", g.owner.mention if g.owner else "?"), ("생성", f"<t:{int(g.created_at.timestamp())}:D>")]: e.add_field(name=k, value=str(v))
    return e
@feat("정보", "서버 아이콘", "서버 아이콘 크게", [])
async def _(i, a):
    if not i.guild.icon: return "아이콘 없음"
    e = emb("아이콘"); e.set_image(url=i.guild.icon.url); return e
@feat("정보", "서버 배너", "서버 배너", [])
async def _(i, a):
    if not i.guild.banner: return "배너 없음"
    e = emb("배너"); e.set_image(url=i.guild.banner.url); return e
@feat("정보", "역할 목록", "서버 역할 전부", [], False, "roles")
async def _(i, a): return emb("역할", " ".join(r.mention for r in reversed(i.guild.roles[1:]))[:4000])
@feat("정보", "역할 정보", "역할 상세", [P("r", "역할", "role")])
async def _(i, a): r = a["r"]; return emb(r.name, f"ID {r.id} · 멤버 {len(r.members)} · 색 #{r.colour.value:06X} · 생성 <t:{int(r.created_at.timestamp())}:D>", r.colour.value or 0x5865F2)
@feat("정보", "채널 목록", "텍스트/음성 채널", [])
async def _(i, a): return emb("채널", f"텍스트 {len(i.guild.text_channels)} · 음성 {len(i.guild.voice_channels)}\n" + " ".join(c.mention for c in i.guild.text_channels[:50]))
@feat("정보", "채널 정보", "현재 채널 상세", [])
async def _(i, a): c = i.channel; return f"#{c.name} · ID {c.id} · 생성 <t:{int(c.created_at.timestamp())}:D> · 슬로우 {getattr(c, 'slowmode_delay', 0)}s · 주제: {getattr(c, 'topic', None) or '-'}"
@feat("정보", "이모지 목록", "서버 커스텀 이모지", [], False, "emoji")
async def _(i, a): return " ".join(str(e) for e in i.guild.emojis[:80]) or "없음"
@feat("정보", "스티커 목록", "서버 스티커", [])
async def _(i, a): return ", ".join(s.name for s in i.guild.stickers) or "없음"
@feat("정보", "멤버 수", "인원/봇/온라인", [], False, "members")
async def _(i, a): ms = i.guild.members; return f"👥 총 {len(ms)} · 사람 {sum(1 for m in ms if not m.bot)} · 봇 {sum(1 for m in ms if m.bot)} · 온라인 {sum(1 for m in ms if m.status != discord.Status.offline)}"
@feat("정보", "음성 채널 인원", "음성 채널별 접속자", [])
async def _(i, a): return "\n".join(f"🔊 {c.name}: {', '.join(m.display_name for m in c.members)}" for c in i.guild.voice_channels if c.members) or "아무도 없음"
@feat("정보", "부스터 목록", "서버 부스터", [])
async def _(i, a): return ", ".join(m.display_name for m in i.guild.premium_subscribers) or "없음"
@feat("정보", "서버 오너", "서버 주인", [])
async def _(i, a): return f"👑 {i.guild.owner.mention if i.guild.owner else '?'}"
@feat("정보", "서버 생성일", "D+며칠", [])
async def _(i, a): return f"📅 <t:{int(i.guild.created_at.timestamp())}:D> (D+{(datetime.datetime.now(datetime.timezone.utc) - i.guild.created_at).days})"
@feat("정보", "고정 메시지", "채널 고정 메시지 수", [])
async def _(i, a): ps = await i.channel.pins(); return f"📌 {len(ps)}개\n" + "\n".join(f"- {p.jump_url}" for p in ps[:10])
@feat("정보", "역할 색상 보기", "역할 색 미리보기", [P("r", "역할", "role")])
async def _(i, a): return emb(f"#{a['r'].colour.value:06X}", color=a["r"].colour.value)
@feat("정보", "최근 가입 5명", "최근 입장 멤버", [])
async def _(i, a): ms = sorted((m for m in i.guild.members if m.joined_at), key=lambda m: m.joined_at, reverse=True)[:5]; return "\n".join(f"{m.display_name} <t:{int(m.joined_at.timestamp())}:R>" for m in ms)
@feat("정보", "가장 오래된 멤버 5명", "초창기 멤버", [])
async def _(i, a): ms = sorted((m for m in i.guild.members if m.joined_at), key=lambda m: m.joined_at)[:5]; return "\n".join(f"{m.display_name} <t:{int(m.joined_at.timestamp())}:D>" for m in ms)
@feat("정보", "역할 인원 통계", "역할별 인원 TOP 15", [])
async def _(i, a): rs = sorted(i.guild.roles[1:], key=lambda r: -len(r.members))[:15]; return "\n".join(f"{r.mention} {len(r.members)}" for r in rs)
@feat("정보", "용어 사전 (검색)", "가강전 용어 뜻", [P("t", "용어")], False, "term")
async def _(i, a): hits = {k: v for k, v in TERMS.items() if a["t"].lower() in k.lower() or a["t"] in v}; return "\n".join(f"**{k}** — {v}" for k, v in list(hits.items())[:10]) or "없음"
for _k, _v in TERMS.items():
    def _mk(k=_k, v=_v):
        async def fn(i, a): return f"📖 **{k}** — {v}"
        return fn
    add_feat("용어", f"용어: {_k}", _v[:60], _mk(), [], False, "term 사전")
@feat("정보", "조작키", "가강전 기본 조작", [], False, "controls")
async def _(i, a): return emb("🎮 조작키", "M1 좌클릭 · 스킬 1~4 · 대시 Q · 가드 F · 각성 G · 이모트 B · 달리기 W 두 번 · 락온 R")

# ───────── 텍스트 도구 ─────────
TXT = {"대문자": lambda s: s.upper(), "소문자": lambda s: s.lower(), "뒤집기": lambda s: s[::-1], "글자수": lambda s: f"{len(s)}자 (공백 제외 {len(s.replace(' ', ''))})",
       "단어수": lambda s: f"{len(s.split())}단어", "스포일러": lambda s: f"||{s}||", "굵게": lambda s: f"**{s}**", "기울임": lambda s: f"*{s}*", "취소선": lambda s: f"~~{s}~~",
       "밑줄": lambda s: f"__{s}__", "코드블록": lambda s: f"```\n{s}\n```", "인라인코드": lambda s: f"`{s}`", "인용": lambda s: "\n".join("> " + l for l in s.splitlines()),
       "세로쓰기": lambda s: "\n".join(s), "공백제거": lambda s: s.replace(" ", ""), "글자섞기": lambda s: "".join(random.sample(s, len(s))), "단어섞기": lambda s: " ".join(random.sample(s.split(), len(s.split()))),
       "이진수": lambda s: " ".join(format(ord(c), "b") for c in s), "16진수": lambda s: s.encode().hex(), "base64 인코딩": lambda s: base64.b64encode(s.encode()).decode(),
       "base64 디코딩": lambda s: base64.b64decode(s.encode()).decode(errors="replace"), "URL 인코딩": lambda s: urllib.parse.quote(s), "URL 디코딩": lambda s: urllib.parse.unquote(s),
       "MD5": lambda s: hashlib.md5(s.encode()).hexdigest(), "SHA1": lambda s: hashlib.sha1(s.encode()).hexdigest(), "SHA256": lambda s: hashlib.sha256(s.encode()).hexdigest(),
       "모스부호": lambda s: " ".join({"a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.", "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..", "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.", "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-", "y": "-.--", "z": "--..", " ": "/"}.get(c, "?") for c in s.lower()),
       "자모 분리": lambda s: "".join((lambda c: (chr(0x1100 + (ord(c) - 0xAC00) // 588) + chr(0x1161 + (ord(c) - 0xAC00) % 588 // 28) + (chr(0x11A7 + (ord(c) - 0xAC00) % 28) if (ord(c) - 0xAC00) % 28 else "")) if 0xAC00 <= ord(c) <= 0xD7A3 else c)(c) for c in s),
       "이모지 글자": lambda s: " ".join(f":regional_indicator_{c}:" if c.isalpha() and c.isascii() else c for c in s.lower()), "반복 3회": lambda s: (s + " ") * 3, "역순 단어": lambda s: " ".join(s.split()[::-1]),
       "첫글자 대문자": lambda s: s.title(), "ㅋ 추가": lambda s: s + "ㅋ" * random.randint(2, 8), "느낌표 강조": lambda s: s.upper() + "!!!", "팰린드롬 검사": lambda s: "✅ 회문" if s.replace(" ", "") == s.replace(" ", "")[::-1] else "❌ 회문 아님",
       "문자 빈도": lambda s: ", ".join(f"{c}:{s.count(c)}" for c in sorted(set(s.replace(' ', '')), key=lambda c: -s.count(c))[:10]), "유니코드": lambda s: " ".join(f"U+{ord(c):04X}" for c in s[:30]),
       "숫자만": lambda s: "".join(c for c in s if c.isdigit()) or "없음", "문자만": lambda s: "".join(c for c in s if c.isalpha()), "줄 수": lambda s: f"{len(s.splitlines())}줄", "줄 정렬": lambda s: "\n".join(sorted(s.splitlines())),
       "중복 줄 제거": lambda s: "\n".join(dict.fromkeys(s.splitlines())), "쉼표→줄바꿈": lambda s: s.replace(",", "\n"), "줄바꿈→쉼표": lambda s: ", ".join(s.splitlines())}
for _k, _f in TXT.items():
    def _mk(f=_f):
        async def fn(i, a):
            try: return str(f(a["t"]))[:1900]
            except Exception as e: raise FeatErr(f"변환 실패: {e}")
        return fn
    add_feat("텍스트 도구", _k, f"텍스트 {_k}", _mk(), [P("t", "내용", "str")], False, "text 문자")
@feat("텍스트 도구", "찾아 바꾸기", "문자열 치환", [P("t", "내용", "str"), P("x", "찾을 것"), P("y", "바꿀 것", required=False)])
async def _(i, a): return a["t"].replace(a["x"], a["y"] or "")[:1900]
@feat("텍스트 도구", "글자 반복", "N회 반복", [P("t", "내용"), P("n", "횟수", "int", lo=1, hi=50)])
async def _(i, a): return (a["t"] * a["n"])[:1900]
@feat("텍스트 도구", "카운트다운 텍스트", "N부터 1까지", [P("n", "시작", "int", lo=1, hi=100)])
async def _(i, a): return " ".join(str(x) for x in range(a["n"], 0, -1))

# ───────── 계산 ─────────
def _safe_eval(s):
    if any(ch not in "0123456789+-*/(). %" for ch in s): raise FeatErr("숫자와 + - * / % ( ) 만")
    try: return eval(s, {"__builtins__": {}}, {})
    except Exception: raise FeatErr("계산 오류")
@feat("계산", "계산기", "사칙연산", [P("s", "식")], False, "calc")
async def _(i, a): return f"🧮 `{a['s']}` = **{_safe_eval(a['s'])}**"
CALC = {"퍼센트 (A의 B%)": (["a", "b"], lambda a, b: a * b / 100), "비율 (A는 B의 몇%)": (["a", "b"], lambda a, b: a / b * 100 if b else 0), "증감률 (A→B)": (["a", "b"], lambda a, b: (b - a) / a * 100 if a else 0),
        "제곱": (["a"], lambda a: a ** 2), "세제곱": (["a"], lambda a: a ** 3), "제곱근": (["a"], lambda a: math.sqrt(a)), "거듭제곱 A^B": (["a", "b"], lambda a, b: a ** b),
        "팩토리얼": (["a"], lambda a: math.factorial(int(a)) if a <= 170 else "너무 큼"), "최대공약수": (["a", "b"], lambda a, b: math.gcd(int(a), int(b))), "최소공배수": (["a", "b"], lambda a, b: abs(int(a) * int(b)) // math.gcd(int(a), int(b)) if a and b else 0),
        "소수 판별": (["a"], lambda a: "소수" if int(a) > 1 and all(int(a) % k for k in range(2, int(math.sqrt(a)) + 1)) else "소수 아님"), "피보나치 N번째": (["a"], lambda a: (lambda n: [0, 1][n] if n < 2 else __import__('functools').reduce(lambda x, _: (x[1], x[0] + x[1]), range(n - 1), (0, 1))[1])(min(int(a), 1000))),
        "나머지 A%B": (["a", "b"], lambda a, b: a % b if b else 0), "몫 A//B": (["a", "b"], lambda a, b: a // b if b else 0), "절댓값": (["a"], lambda a: abs(a)), "반올림": (["a"], lambda a: round(a)),
        "로그 (밑10)": (["a"], lambda a: math.log10(a)), "자연로그": (["a"], lambda a: math.log(a)), "사인(도)": (["a"], lambda a: math.sin(math.radians(a))), "코사인(도)": (["a"], lambda a: math.cos(math.radians(a))),
        "탄젠트(도)": (["a"], lambda a: math.tan(math.radians(a))), "원 넓이 (반지름)": (["a"], lambda a: math.pi * a * a), "원 둘레 (반지름)": (["a"], lambda a: 2 * math.pi * a), "직각삼각형 빗변": (["a", "b"], lambda a, b: math.hypot(a, b)),
        "BMI (kg, cm)": (["a", "b"], lambda a, b: a / (b / 100) ** 2 if b else 0), "2진수 변환": (["a"], lambda a: bin(int(a))[2:]), "8진수 변환": (["a"], lambda a: oct(int(a))[2:]), "16진수 변환": (["a"], lambda a: hex(int(a))[2:].upper()),
        "로마 숫자": (["a"], lambda a: "".join(s * ((int(a) % d_prev if d_prev else int(a)) // d) for d, d_prev, s in [(1000, 0, "M"), (900, 1000, "CM"), (500, 1000, "D"), (400, 500, "CD"), (100, 500, "C"), (90, 100, "XC"), (50, 100, "L"), (40, 50, "XL"), (10, 50, "X"), (9, 10, "IX"), (5, 10, "V"), (4, 5, "IV"), (1, 5, "I")]) if 0 < int(a) < 4000 else "1~3999"),
        "복리 (원금,연이율%,년)": (["a", "b", "c"], lambda a, b, c: a * (1 + b / 100) ** c), "속도 (거리km, 시간h)": (["a", "b"], lambda a, b: a / b if b else 0), "할인가 (가격, 할인%)": (["a", "b"], lambda a, b: a * (1 - b / 100)),
        "전투력 승리 필요횟수 (목표, 현재, 승당)": (["a", "b", "c"], lambda a, b, c: math.ceil((a - b) / c) if c else 0)}
for _k, (_ps, _f) in CALC.items():
    def _mk(ps=_ps, f=_f):
        async def fn(i, a):
            try: r = f(*[a[p] for p in ps])
            except (ValueError, OverflowError, ZeroDivisionError) as e: raise FeatErr(f"계산 불가: {e}")
            return f"🧮 **{round(r, 6) if isinstance(r, float) else r}**"
        return fn
    add_feat("계산", _k, f"{_k} 계산", _mk(), [P(p, p.upper(), "float") for p in _ps], False, "calc math 수학")
@feat("계산", "평균", "숫자들 평균/합/최대/최소", [P("l", "숫자들", "list")], False, "avg")
async def _(i, a):
    try: ns = [float(x) for x in a["l"]]
    except ValueError: raise FeatErr("숫자만")
    return f"합 {sum(ns):g} · 평균 {sum(ns) / len(ns):g} · 최대 {max(ns):g} · 최소 {min(ns):g} · 개수 {len(ns)}"
@feat("계산", "진법 변환 (임의)", "수, 현재 진법, 목표 진법", [P("s", "수"), P("a", "현재 진법", "int", lo=2, hi=36), P("b", "목표 진법", "int", lo=2, hi=36)])
async def _(i, a):
    try: n = int(a["s"], a["a"])
    except ValueError: raise FeatErr("변환 불가")
    d = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"; out = ""
    while n: out = d[n % a["b"]] + out; n //= a["b"]
    return out or "0"
for _u1, _u2, _f in UNITS:
    def _mk(u1=_u1, u2=_u2, f=_f):
        async def fn(i, a): return f"📐 {a['v']:g} {u1} = **{a['v'] * f:,.4g} {u2}**"
        return fn
    def _mk2(u1=_u1, u2=_u2, f=_f):
        async def fn(i, a): return f"📐 {a['v']:g} {u2} = **{a['v'] / f:,.4g} {u1}**"
        return fn
    add_feat("단위 변환", f"{_u1} → {_u2}", f"{_u1}을 {_u2}로", _mk(), [P("v", f"{_u1} 값", "float")], False, "unit 변환")
    add_feat("단위 변환", f"{_u2} → {_u1}", f"{_u2}을 {_u1}로", _mk2(), [P("v", f"{_u2} 값", "float")], False, "unit 변환")
@feat("단위 변환", "섭씨 → 화씨", "°C → °F", [P("v", "섭씨", "float")])
async def _(i, a): return f"🌡️ {a['v']:g}°C = **{a['v'] * 9 / 5 + 32:.1f}°F**"
@feat("단위 변환", "화씨 → 섭씨", "°F → °C", [P("v", "화씨", "float")])
async def _(i, a): return f"🌡️ {a['v']:g}°F = **{(a['v'] - 32) * 5 / 9:.1f}°C**"

# ───────── 시간 ─────────
def now_utc(): return datetime.datetime.now(datetime.timezone.utc)
for _city, _off in TZ.items():
    def _mk(city=_city, off=_off):
        async def fn(i, a): t = now_utc() + datetime.timedelta(hours=off); return f"🕒 {city} (UTC{off:+d}): **{t:%Y-%m-%d %H:%M}**"
        return fn
    add_feat("시간", f"{_city} 현재 시간", f"{_city} 시각", _mk(), [], False, "time 시계 timezone")
@feat("시간", "현재 시간 (KST)", "한국 시간", [], False, "time now")
async def _(i, a): t = now_utc() + datetime.timedelta(hours=9); return f"🕒 **{t:%Y-%m-%d %H:%M:%S}** (KST) · <t:{int(time.time())}:F>"
@feat("시간", "타임스탬프 만들기", "날짜 → 디스코드 타임스탬프", [P("d", "날짜 (YYYY-MM-DD HH:MM, KST)")], False, "timestamp")
async def _(i, a):
    try: dt = datetime.datetime.strptime(a["d"].strip(), "%Y-%m-%d %H:%M") if ":" in a["d"] else datetime.datetime.strptime(a["d"].strip(), "%Y-%m-%d")
    except ValueError: raise FeatErr("형식: 2026-01-01 20:00")
    ts = int((dt - datetime.timedelta(hours=9)).replace(tzinfo=datetime.timezone.utc).timestamp())
    return f"`<t:{ts}:F>` → <t:{ts}:F>\n`<t:{ts}:R>` → <t:{ts}:R>"
@feat("시간", "타임스탬프 해석", "숫자 → 날짜", [P("n", "타임스탬프", "int")])
async def _(i, a): return f"<t:{a['n']}:F> (<t:{a['n']}:R>)"
@feat("시간", "D-day 계산", "날짜까지 며칠", [P("d", "날짜 YYYY-MM-DD")], False, "dday")
async def _(i, a):
    try: d = datetime.date.fromisoformat(a["d"].strip())
    except ValueError: raise FeatErr("형식: 2026-12-25")
    n = (d - (now_utc() + datetime.timedelta(hours=9)).date()).days; return f"📅 {d}: **D{'-' if n > 0 else '+'}{abs(n)}**" if n else "📅 오늘!"
@feat("시간", "요일 계산", "날짜의 요일", [P("d", "날짜 YYYY-MM-DD")])
async def _(i, a):
    try: d = datetime.date.fromisoformat(a["d"].strip())
    except ValueError: raise FeatErr("형식: 2026-12-25")
    return f"📅 {d} = **{'월화수목금토일'[d.weekday()]}요일**"
@feat("시간", "날짜 더하기", "오늘 + N일", [P("n", "일수", "int")])
async def _(i, a): d = (now_utc() + datetime.timedelta(hours=9)).date() + datetime.timedelta(days=a["n"]); return f"📅 {d} ({'월화수목금토일'[d.weekday()]})"
@feat("시간", "두 날짜 차이", "A와 B 사이 일수", [P("a", "날짜1"), P("b", "날짜2")])
async def _(i, a):
    try: return f"📅 {abs((datetime.date.fromisoformat(a['a'].strip()) - datetime.date.fromisoformat(a['b'].strip())).days)}일"
    except ValueError: raise FeatErr("형식: 2026-12-25")
@feat("시간", "올해 남은 날", "연말까지", [])
async def _(i, a): t = (now_utc() + datetime.timedelta(hours=9)).date(); return f"📅 {(datetime.date(t.year, 12, 31) - t).days}일 남음"
@feat("시간", "오늘 며칠째", "올해 N번째 날", [])
async def _(i, a): t = (now_utc() + datetime.timedelta(hours=9)).date(); return f"📅 {t.timetuple().tm_yday}일째 · {t.isocalendar()[1]}주차"
@feat("시간", "세계 시간표", "주요 도시 한눈에", [])
async def _(i, a): return emb("🌍 세계 시간", "\n".join(f"{c}: {(now_utc() + datetime.timedelta(hours=o)):%m-%d %H:%M}" for c, o in TZ.items()))
@feat("시간", "스톱워치 시작", "시작 시각 기록 (DM 없음)", [])
async def _(i, a): STOPWATCH[i.user.id] = time.monotonic(); return "⏱️ 시작!"
@feat("시간", "스톱워치 확인", "경과 시간", [])
async def _(i, a):
    if i.user.id not in STOPWATCH: raise FeatErr("먼저 시작하세요")
    return f"⏱️ {time.monotonic() - STOPWATCH[i.user.id]:.1f}초 경과"
STOPWATCH = {}

# ───────── 캐릭터 × 티어 운용법 (생성) ─────────
TIER_ADVICE = {"브론즈": "기본 M1 콤보와 대시 타이밍만 익혀도 충분", "실버": "가드와 잡기 구분을 몸에 익히기", "골드": "벽콤과 스킬 캔슬 연습 시작", "플래티넘": "상대 캐릭 스킬 쿨 암기 필수",
               "다이아": "심리전과 대시 베이팅 활용", "마스터": "콤보 리셋과 프레임 이득 계산", "그랜드마스터": "매치업별 전용 콤보 루트", "S급 히어로": "모든 캐릭 상성·카운터 완벽 숙지"}
for _c, _d in CHARS.items():
    for _t in TIERS:
        def _mk(c=_c, d=_d, tn=_t[1], te=_t[2]):
            async def fn(i, a): return emb(f"{te} {tn} 구간 {c} 운용법", f"**이 구간 핵심**: {TIER_ADVICE[tn]}\n**{c} 포인트**: {d['tip']}\n**추천 연습 스킬**: {d['skills'][TIERS.index(tier_of(TIERS[[t[1] for t in TIERS].index(tn)][0])) % 4]}\n**상대법 대비**: {d['counter']}")
            return fn
        add_feat("티어별 운용", f"{_t[1]} {_c} 운용법", f"{_t[1]} 구간에서 {_c} 플레이 가이드", _mk(), [], False, "guide 운용 가이드")

# ───────── 랜덤 뽑기 ─────────
@feat("랜덤 뽑기", "클랜원 랜덤 1명", "등록 클랜원 중 랜덤", [], False, "random pick")
async def _(i, a): rows = qa("SELECT user FROM members WHERE guild=? AND roblox IS NOT NULL", i.guild_id); return f"🎯 {name_of(i.guild, random.choice(rows)['user'])}" if rows else "없음"
@feat("랜덤 뽑기", "역할 랜덤 멤버", "역할 보유자 중 랜덤", [P("r", "역할", "role")])
async def _(i, a): return f"🎯 {random.choice(a['r'].members).display_name}" if a["r"].members else "없음"
@feat("랜덤 뽑기", "음성 채널 랜덤 멤버", "내 음성 채널에서 랜덤", [])
async def _(i, a):
    vc = i.user.voice and i.user.voice.channel
    if not vc or not vc.members: raise FeatErr("음성 채널 필요")
    return f"🎯 {random.choice(vc.members).display_name}"
@feat("랜덤 뽑기", "온라인 랜덤 멤버", "온라인 멤버 중 랜덤", [])
async def _(i, a): ms = [m for m in i.guild.members if not m.bot and m.status != discord.Status.offline]; return f"🎯 {random.choice(ms).display_name}" if ms else "없음"
@feat("랜덤 뽑기", "오늘의 MVP 후보", "활동점수 상위 중 랜덤", [])
async def _(i, a): rows = qa("SELECT user FROM members WHERE guild=? ORDER BY activity DESC LIMIT 5", i.guild_id); return f"🏅 {name_of(i.guild, random.choice(rows)['user'])}" if rows else "없음"
@feat("랜덤 뽑기", "랜덤 티어 멤버", "티어 지정 랜덤", [P("t", "티어 이름")])
async def _(i, a): rows = [r for r in qa("SELECT user, power FROM members WHERE guild=?", i.guild_id) if tier_of(r["power"])[1] == a["t"]]; return f"🎯 {name_of(i.guild, random.choice(rows)['user'])}" if rows else "없음"
@feat("랜덤 뽑기", "캐릭 2개 조합", "메인+서브 추천", [])
async def _(i, a): x, y = random.sample(CHAR_LIST, 2); return f"🎭 메인 **{x}** / 서브 **{y}**"
@feat("랜덤 뽑기", "명언 공개로 보내기", "채널에 명언 게시", [])
async def _(i, a): await i.channel.send(f"📜 {random.choice(QUOTES)}"); return "✅"
@feat("랜덤 뽑기", "밈 공개로 보내기", "채널에 밈 게시", [])
async def _(i, a): await i.channel.send(f"😂 {random.choice(MEMES)}"); return "✅"
@feat("랜덤 뽑기", "팁 공개로 보내기", "채널에 팁 게시", [])
async def _(i, a): await i.channel.send(f"💡 {random.choice(TIPS)}"); return "✅"
@feat("랜덤 뽑기", "랜덤 1v1 매칭", "클랜원 둘 매칭 제안", [])
async def _(i, a):
    rows = qa("SELECT user FROM members WHERE guild=? AND roblox IS NOT NULL", i.guild_id)
    if len(rows) < 2: raise FeatErr("클랜원 부족")
    x, y = random.sample(rows, 2); return f"⚔️ 오늘의 스파링: {name_of(i.guild, x['user'])} vs {name_of(i.guild, y['user'])}"
@feat("랜덤 뽑기", "내 상대 추천", "비슷한 전투력 랜덤 1명", [])
async def _(i, a):
    p = mrow(i.guild_id, i.user.id)["power"]
    rows = qa("SELECT user FROM members WHERE guild=? AND user!=? AND power BETWEEN ? AND ?", i.guild_id, i.user.id, int(p * 0.7), int(p * 1.3) + 100)
    return f"⚔️ 추천 상대: {name_of(i.guild, random.choice(rows)['user'])}" if rows else "비슷한 상대 없음"

# ═══════════════════════════ 슬래시 명령어 (최소) ═══════════════════════════
START_TS = int(time.time())

@tree.command(name="패널", description="[관리자] 버튼 패널 설치")
@app_commands.default_permissions(manage_guild=True)
async def 패널(inter: discord.Interaction, 채널: Optional[discord.TextChannel] = None):
    if not is_admin(inter): return await reply(inter, "⛔ 관리자만")
    await (채널 or inter.channel).send(embed=panel_embed(inter.guild), view=PanelView()); await reply(inter, "✅ 패널 설치 완료")

@tree.command(name="help", description="도움말 (본인만 보임)")
async def help_cmd(inter: discord.Interaction): await reply(inter, help_embed(inter))

@tree.command(name="검색", description="기능 검색 (본인만 보임)")
async def 검색(inter: discord.Interaction, 키워드: str):
    feats = search(키워드, is_admin(inter))
    if not feats: return await reply(inter, f"🔍 `{키워드}` 결과 없음")
    e = emb(f"🔍 '{키워드}' {len(feats)}개", "\n".join(feature_line(f) for f in feats), 0x1ABC9C)
    await reply(inter, e, ResultsView(feats))

@tree.command(name="실행", description="기능 번호로 실행")
async def 실행(inter: discord.Interaction, 번호: str):
    f = FEATURES.get(번호.strip().zfill(4))
    if not f: return await reply(inter, "그 번호의 기능이 없어요.")
    await run_feature(inter, f)

@tree.command(name="티밍", description="티밍 당했을 때 클랜원 호출")
async def 티밍(inter: discord.Interaction, 링크: Optional[str] = None, 상황: str = "티밍 당하는 중!"): await send_teaming(inter, 링크, 상황)

@tree.command(name="카테고리", description="카테고리별 기능 보기 (본인만 보임)")
async def 카테고리(inter: discord.Interaction): await reply(inter, "📂 카테고리를 선택하세요.", CategoryView(is_admin(inter)))

# ═══════════════════════════ 이벤트 ═══════════════════════════
@bot.event
async def on_ready():
    await tree.sync()
    for g in bot.guilds:
        tree.copy_global_to(guild=g)
        try: await tree.sync(guild=g)
        except discord.HTTPException: pass
    await bot.change_presence(activity=discord.Game(f"가강전 클랜 | 기능 {len(FEATURES):,}개 | /help"))
    print(f"✅ 로그인: {bot.user} · 서버 {len(bot.guilds)}개 · 기능 {len(FEATURES):,}개")

@bot.event
async def on_member_join(member):
    c = cfg(member.guild.id)
    if c["welcome_ch"] and (ch := member.guild.get_channel(c["welcome_ch"])):
        msg = c["welcome_msg"] or "{user}님 환영합니다! 패널에서 📖 help 를 눌러보세요."
        await ch.send(msg.replace("{user}", member.mention).replace("{server}", member.guild.name))

_spam = {}
@bot.event
async def on_message(msg):
    if msg.author.bot or not msg.guild: return
    c = cfg(msg.guild.id)
    if isinstance(msg.author, discord.Member) and msg.author.guild_permissions.manage_messages: return
    if c["automod_badword"]:
        words = [r["word"] for r in qa("SELECT word FROM badwords WHERE guild=?", msg.guild.id)]
        if any(w in msg.content for w in words):
            await msg.delete(); await msg.channel.send(f"🚫 {msg.author.mention} 금지어 삭제", delete_after=5); return
    if c["automod_link"] and ("http://" in msg.content or "https://" in msg.content or "discord.gg/" in msg.content):
        await msg.delete(); await msg.channel.send(f"🚫 {msg.author.mention} 링크 금지", delete_after=5); return
    if c["automod_spam"]:
        key = (msg.guild.id, msg.author.id); now = time.time()
        _spam[key] = [t for t in _spam.get(key, []) if now - t < 5] + [now]
        if len(_spam[key]) >= 6:
            _spam[key] = []
            try: await msg.author.timeout(datetime.timedelta(minutes=1), reason="도배"); await msg.channel.send(f"🚫 {msg.author.mention} 도배 1분 타임아웃", delete_after=5)
            except discord.Forbidden: pass

@tree.error
async def on_app_error(inter, error):
    msg = f"❌ 오류: {error.original if isinstance(error, app_commands.CommandInvokeError) else type(error).__name__}"
    try: await reply(inter, msg)
    except discord.HTTPException: pass

if __name__ == "__main__":
    print(f"기능 {len(FEATURES):,}개 / 카테고리 {len(CATS)}개 로드됨")
    if TOKEN == "여기에_봇_토큰_입력": print("⚠️ dc.py 상단 TOKEN 에 봇 토큰을 넣어주세요.")
    bot.run(TOKEN)
