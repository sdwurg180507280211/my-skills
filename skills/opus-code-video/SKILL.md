---
name: opus-code-video
description: 纯靠 Claude 写代码做视频，不调视频或图片生成模型：画面是网页逐帧渲染的 MG 动画，配乐和音效用代码合成，旁白用豆包语音 2.0 并按逐字时间戳重排节拍、生成字幕，最后渲染、质检、出封面。用户要做技术解说、知识科普、MG 动画短片，提到"用 Opus/Claude 写代码做视频"、mg-styles-15、代码动画、renderAt 逐帧渲染，或延续这类工程时使用；要用 Seedance 等模型生成写实画面的短剧用 seedance-short-drama。
---

# 纯 Opus 写代码做视频

你是导演、动效设计、工程师和音响师。用户只做三件事：定题材和方向、确认旁白稿、看片提意见。画面、动画、配乐、字幕、渲染和自检都由你完成。

成本几乎只有 Claude 的用量：不调视频模型；旁白用豆包语音，1 分钟约 250 字，新账号有 2 万字免费额度。

一类做法，多种风格：每种风格在 `styles/<名>/` 下有说明和一支可运行的示例片，新片从示例复制开始，换内容不换骨架。现有风格：

| 风格 | 适合 | 示例 |
|---|---|---|
| [sticker-explainer](styles/sticker-explainer/README.md) 贴纸科普 | 讲流程、原理、"一件事背后发生了什么" | 《按下回车之后的 1 秒》：横屏，60 秒无配音 / 67.5 秒带旁白和字幕 |

用户想要的风格不在表里（例如睡前故事）时，照下面的流程先做一支，跑通后再按同样结构加进 `styles/`。

## 开工前

- 依赖：Node 22+、Google Chrome、ffmpeg、Python 3.10+。
- 新建工程：`bash scripts/new_project.sh <工程目录> [风格]`。它会稀疏克隆 mg-styles-15（MIT，渲染器 `harness/render.mjs` 和配乐工具 mgaudio），复制风格示例，装 puppeteer-core 和配乐依赖（Intel Mac 上 numba 新版没有安装包，脚本会装 0.60），下载 OFL 字体。
- 旁白要豆包语音的 API Key，开通和费用见 [references/narration.md](references/narration.md)。

## 流程

1. **定题**：只问看不出来的事：发在哪（横屏还是竖屏）、给谁看、要不要旁白、片长。科普的事实要能核实；示意数字标"示例"，网址和 IP 用文档专用的（`example.com`、`203.0.113.x`）。
2. **剧本与自查**：旁白稿写成表格（时间、段落、画面、旁白），连同定位和事实边界写进剧本。不交外部模型审稿（Gemini、DeepSeek 都不用，用户 2026-10-29 定的）。自己逐条过：事实对照官方文档或论文原文、示意数字标「示例」、对照教训、每句字数和节奏，结果记进剧本末尾的「自查」一节，再交用户批，批了才定稿。定稿前不配音、不渲染整片。故事类（如睡前故事）先写画面剧本、做无声版，静音看得懂再定配音。
3. **节拍表**（`film/cues_base.json`）：钩子在开头 0.5 秒内出现，每章 6～10 秒（新概念至少停 7 秒）；片长按“讲没讲透”定，不卡“超没超时”，太赶的段加句子（见 narration.md），高潮在 60～85% 处，结尾停 1 秒以上。画面和配乐都只从这里读时间，不在代码里写死秒数。有旁白时可以先定稿配音，再按逐字时间戳生成节拍，见 [render-and-qc.md 的教训](references/render-and-qc.md)。
4. **关键帧**：先写画面，渲染 6～10 张关键帧（`node harness/render.mjs film --stills …`），逐张看构图、层级、压线、安全区、字号，改到满意再做动作。检查项和这次踩过的坑见 [references/render-and-qc.md](references/render-and-qc.md)。
5. **配乐**（`film/audio.py`，用工程的 `.venv` 跑）：mgaudio 选配方，音效按节拍表放，砸点前抽空；输出 `film/out/bed.wav`。
6. **旁白**（可选）：
   - 旁白稿按第 2 步定稿、用户确认后才合成。
   - 先用 4～5 个候选音色合成同一段试音，报时长，由用户挑选。
   - 合成整稿：`scripts/doubao_tts.py lines <音色> <工程>`。
   - 重排节拍：`scripts/retime.py <工程>`，以配音为准拉长画面，生成 `cues.json` 里的字幕。
   - 混音：`scripts/mix_voice.py <工程>`，说话处配乐压低 8 dB，整体 -14 LUFS。
   - 删掉和旁白重复的画面文字，给底部字幕让位。
7. **渲染**：`node harness/render.mjs film --mb 8 --workers 4`。运动模糊用 8 次采样，3 次会出叠影。
8. **质检**：`scripts/qc.py <成片> --duration <秒>`，每 1～2 秒抽帧拼图看节奏（镜头落地后空着的画面、拉远后看不清的字），自评打分，写出最弱的三点，并补进 render-and-qc.md 的教训里。AAC 峰值超了就降音量重新封装，画面不用重渲。
9. **交付**：成片、封面（`cover.py` 出横 4:3、竖 3:4；也可以用生图网关画插画、再叠标题）、发布用的标题和简介，以及一句话说明用量和花费。发布注意事项和角色贴纸做法见 [references/publish.md](references/publish.md)。

## 规矩

- 花钱的事先报价：旁白按字数，超出免费额度要确认。生图网关和渲染不花钱。
- 旁白稿和字幕文字要用户确认；改台词也要确认。
- 素材只用 CC0、OFL、MIT 这类可商用的，记进工程的 `CREDITS.md`。mg-styles-15 的渲染器复制进工程时附上它的 LICENSE。
- 账号名、角色图、头像、Key 都是用户的私有素材，放在用户自己的目录，不写进本仓库；示例片的 `brand` 留空。
- 改片只重做受影响的段落；节拍表、画面、配乐都读同一份 `cues.json`，改一处，三处一起对得上。

## 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/new_project.sh` | 新建工程：渲染器、配乐工具、风格示例、依赖、字体 |
| `scripts/doubao_tts.py` | 豆包语音 2.0：`one` 合成一句试音，`lines` 按旁白稿逐句合成，存逐字时间戳 |
| `scripts/retime.py` | 以配音为准重排节拍：拉长装不下的段、锚定关键字、按标点切字幕 |
| `scripts/mix_voice.py` | 旁白叠到底乐上，统一响度，限峰值 |
| `scripts/qc.py` | 成片规格、响度、峰值、黑帧检查，峰值超标时给出修正命令 |
| `scripts/cutout.py` | 纯色底贴纸抠成透明 PNG |

## 参考

- [references/narration.md](references/narration.md)：豆包语音开通、接口、音色实测、写旁白、节拍跟配音、混音。
- [references/render-and-qc.md](references/render-and-qc.md)：画面代码规矩、关键帧、镜头飞行、渲染参数、质检、事实边界。
- [references/publish.md](references/publish.md)：封面、角色贴纸、抖音发布。
