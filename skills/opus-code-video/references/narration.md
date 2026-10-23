# 旁白配音：豆包语音合成 2.0

## 开通与密钥

- 在火山引擎"豆包语音"控制台建应用；新版控制台只给一个 **API Key**（不再分 AppID / Access Token）。请用户存到 `~/.config/volc-speech/api-key`（权限 600），或设环境变量 `DOUBAO_SPEECH_API_KEY`。不要让用户把 Key 贴进对话；如果已经贴了，存好后提醒他到控制台作废重建。
- 和方舟（视频、图片模型）的 Key 是两套，不能混用。
- 费用（2026-10 官方计费页）：控制台点"试用"送 2 万字符、半年有效；之后按调用后付费 3 元/万字符，不必先买字数包。一条 1 分钟旁白约 250 字。先报字数和金额，超出免费额度要用户确认。

## 接口

- 异步：`POST https://openspeech.bytedance.com/api/v3/tts/submit` 提交，`/api/v3/tts/query` 轮询（`task_status` 2 完成、3 失败），完成后下载 `audio_url`。
- 请求头只要 `X-Api-Key`、`X-Api-Resource-Id: seed-tts-2.0`、`X-Api-Request-Id`。带了旧的 `X-Api-App-Id`/`X-Api-Access-Key` 会报 `load grant: requested grant not found`。
- `audio_params.enable_timestamp: true` 时返回 `sentences[].words[]`（每个字的起止秒数，标点粘在前一个字上），字幕和节拍都以它为准，不按字数估。
- 旧的 V1 接口（`/api/v1/tts`）不支持 2.0 音色，不要用。
- 国内服务，固定直连，不走会话代理。

用 `scripts/doubao_tts.py`：`one` 合成一句试音，`lines` 按 `voice/旁白.txt` 每行一句合成到 `voice/lines/NN.mp3`（同时存 `.json` 时间戳）。

## 音色

2.0 音色 ID 以 `_uranus_bigtts` 结尾，完整列表见官方文档"音色列表"（网页版"在线合成体验"里的 1.0 名字和 2.0 不同）。试音时用同一段含难读词的文字（英文缩写、点 com、数字）合成 4～5 个候选，报每段时长，让用户自己听。实测（同一段 66 字）：

| 音色 | ID | 时长 | 备注 |
|---|---|---:|---|
| 解说小明 | zh_male_jieshuoxiaoming_uranus_bigtts | 12.0 秒 | 男声，最快 |
| 爽快思思 | zh_female_shuangkuaisisi_uranus_bigtts | 12.6 秒 | 女声，干脆 |
| 萌丫头 | zh_female_mengyatou_uranus_bigtts | 13.9 秒 | 女孩声；《按下回车之后》用的这个 |
| 亮嗓萌仔 | zh_male_liangsangmengzai_uranus_bigtts | 14.0 秒 | 男孩声 |
| 磁性解说男声 | zh_male_cixingjieshuonan_uranus_bigtts | 17.4 秒 | 慢，会把片子拉长很多 |
| 奶气萌娃 | zh_male_naiqimengwa_uranus_bigtts | 21.0 秒 | 很慢 |

"佩奇猪""熊二""樱桃丸子"这类模仿动画角色的音色有版权方，用在自己账号上有风险，不推荐。

### 童声：用户挑定的 4 个

萌丫头听感上平翘舌不分，用户换掉了。试音用了一段专门考平翘舌的绕口令（"四是四，十是十，十四是十四，四十是四十。知道就说知道……"），再接一句技术词，一段 71 字。下面 4 个是用户听后保留的，语速也是用户选定的：

| 角色 | 音色 | ID | 语速 | 71 字说话时长 |
|---|---|---|---:|---:|
| 男童 | 天才童声 2.0 | zh_male_tiancaitongsheng_uranus_bigtts | +30 | 15.9 秒 |
| 女童 | 软萌团子 2.0 | ICL_uranus_zh_female_ruanmengtuanzi_tob | -4 | 15.3 秒 |
| 女童 | 活泼女孩 2.0 | ICL_uranus_zh_female_huoponvhai_tob | +3 | 13.4 秒 |
| 讲故事 | 少儿故事 2.0 | zh_female_shaoergushi_uranus_bigtts | 0 | 19.7 秒（偏慢，适合睡前故事） |

- `ICL_uranus_…_tob` 开头的音色同样用 `seed-tts-2.0` 资源调用，实测可以直接用。
- 语速参数和时长不是线性关系：女童本来就快，调慢 4～9 几乎没变化，调快一点就明显变短；男童和讲故事的声音原本偏慢，要 +20～+30 才到每秒约 4.4 字。
- 平翘舌、口音这类听感，只能请用户自己听；时间戳里只有文字，看不出发音。

## 写旁白

- 每章一两句，按每秒约 4 个字估长度；先写成表格（时间、画面、旁白）给用户确认，台词改动都要用户确认。
- 英文缩写照写（DNS、IP、HTML），模型会逐个字母读；"点 com"这种写法读得自然，字幕里再换成 `.com`（`narration.show`）。
- 数字写成汉字（"四百四十一毫秒"），读法可控；字幕可以换回阿拉伯数字。
- 关键数字要和画面同时出现时，在 `narration.place` 里用 `anchor_word` 把这个字钉在事件上（见 retime.py 文档）。

## 节拍跟着配音走

1. 画面先按无配音节奏做好，节拍存为 `film/cues_base.json`，在里面写 `narration` 配置（段落边界 + 每句放哪）。
2. 合成旁白后运行 `scripts/retime.py <工程>`：装不下的段按比例拉长，够长的不动，写出 `film/cues.json`（含 `voice` 和 `subs`）。示例片 60 秒 → 67.5 秒。
3. 画面、配乐都读 `cues.json`，重新出关键帧检查，再渲染。
4. 不为了凑原时长去给旁白加速；必要时整体最多快 10%（`--rate`）。

## 混音

- `audio.py`（风格示例里）出 `film/out/bed.wav`：配乐和音效，-16 LUFS；配乐增益曲线 = 高潮前抽空 和 说话处压低 8 dB（前 0.15 秒、后 0.25 秒，0.12 秒斜坡）取较低者。
- `scripts/mix_voice.py <工程>`：每句旁白统一到 -16 LUFS 放到位，整体 -14 LUFS，alimiter 压在 -1.8 dBFS，写 `film/out/audio.wav`。
- 旁白文件开头有一小段静音，第一句放在片头附近时位置可能是负数，脚本会裁掉多出的静音。
