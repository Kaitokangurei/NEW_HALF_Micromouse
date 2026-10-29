# A10：タイヤ寄りを前壁用10°、機体前方を横壁用60°へ修正

[3Dビューア](../mechanical/assembly-a10.html) / [組立STEP](../mechanical/assembly-a10.step) / [画像](../mechanical/sensor-a10.png) / [メイン基板STEP](../mechanical/pcb-a10-concept.step)

ユーザー指定に合わせ、センサの用途と角度の対応を修正した。**真正面0°、真横90°**。左右とも機体の外向きに角度を付ける。

| 取り付け位置 | 用途 | 左／右の角度 | 基板中心X,Y [mm] |
|---|---|---|---|
| タイヤに近い後側2枚 | 前壁用 | −10°／+10° | X=±14.0、Y=16.5 |
| 機体前方の2枚 | 横壁用 | −60°／+60° | X=±7、Y=7.5 |

基板・発光部・受光部・リード・差込タブを一緒に回転する。タイヤ寄りの2枚は上部固定基板との干渉を避けるため、A09より左右へ各0.4 mm移動した。機体前方の2枚は中心位置を維持する。
メイン基板はA07から差込穴を作り直し、以前の角度の穴を残さない。
部品名の`front_*`は前壁用（タイヤ寄り）、`side_*`は横壁用（機体前方）を表す。位置の前後と測る壁を混同しない。
光軸の水平ベクトルは `(sin θ, −cos θ, 0)`。左が負、右が正。

ファン・駆動部・電池はA09と同じ配置。ToraNekoと同じ発光OSI5FU3A11C・受光LTR-209を各4個、立て基板上で上下に並べる。
基板寸法、取付方法、発光高さ5.4 mm・受光高さ10.1 mmは[A08](sensor-a08.md)を参照。

## 確認範囲

[生成スクリプト](../mechanical/build_sensor_a10.py) / [検査JSON](../mechanical/sensor-a10-checks.json)

新部品と既存部品の交差、差込穴の基板内への収まり、Φ22羽根の回転領域、光軸方向20 mmの遮蔽、STEP再読込と目標外形を検査する。
今回のモデルは97部品・135ソリッド。1730組の静的交差、20組の羽根回転領域、8本の光軸中心線で食い込み・遮蔽を検出しなかった。STEP読み戻しも有効。外接寸法は幅38.8 × 長さ58.719 × 高さ19.887 mm（名目・仮形状）。

**LTR-209の外形は未確認の予約円柱Φ4.2×6**。実物の外形、はんだ・配線・公差、光学性能、振動・固定強度は未検証。
光軸中心線に遮蔽物がないことは、照射範囲全体や実際の測距性能の保証ではない。角度変更に合わせて実測校正する。

```sh
XDG_CACHE_HOME=/tmp/mouse-cad-cache MPLCONFIGDIR=/tmp/mouse-matplotlib /workspace/.tools/mouse-view/bin/python mechanical/build_sensor_a10.py
```

参照CAD：ToraNeko.Mk3、Copyright (c) 2026 Tokoro0917、MIT License。
[ライセンス全文](../mechanical/third_party/ToraNeko.Mk3.LICENSE)を派生出力とともに配布する。
