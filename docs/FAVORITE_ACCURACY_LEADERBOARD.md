# 🏆 BetScout Opening-Odds Favorite Accuracy Leaderboard (`65,078` Verified Matches)

This report ranks teams and players across all major sports by **Opening-Odds Favorite Accuracy** — how reliably they convert clear favorite status (`Opening Odds <= 1.65`, Implied Win Probability `>= 58%`) into outright victories.

- **Data Scope:** `65,078` verified matches in `data/betscout.db` (`15,922` priced team matches with opening/closing odds + `43,649` ATP/WTA Tennis matches).
- **Calibration Edge (`Actual − Exp`):** Percentage-point difference between realized Win% and de-vigged opening-odds implied probability.
- **Model Integration:** Directly factored into BetScout's **Best Bets Conviction Score (`0–100` `edge_score`)**, **Team/Player Scout (`Fav: XW-YL`)**, and **Paper-Tiger Favorite Fade (`fade_trap`)** gates.

---

## 1. Global Cross-Sport Top 40 Most Accurate Favorites (Sorted by Win% on Top)

| Rank | Team / Player | Sport & Competition | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **New England Patriots** | 🏈 NFL (nfl) | `10W – 0L` | **`100.0%`** | `@ 1.34` | `72.5%` | **`+27.5pp`** | **`+34.0%` (`+3.40u`)** |
| **2** | **Dutton, Stuart** | 🎯 Darts (darts) | `7W – 0L` | **`100.0%`** | `@ 1.30` | `75.8%` | **`+24.2pp`** | **`+29.9%` (`+2.09u`)** |
| **3** | **Marie Bouzkova** | 🎾 Tennis (WTA) | `21W – 1L` | **`95.5%`** | `@ 1.27` | `75.5%` | **`+20.0pp`** | **`+21.2%` (`+4.66u`)** |
| **4** | **Ashlyn Krueger** | 🎾 Tennis (WTA) | `19W – 1L` | **`95.0%`** | `@ 1.30` | `73.6%` | **`+21.4pp`** | **`+23.2%` (`+4.64u`)** |
| **5** | **Jannik Sinner** | 🎾 Tennis (ATP) | `75W – 5L` | **`93.8%`** | `@ 1.07` | `89.9%` | **`+3.9pp`** | **`-0.1%` (`-0.05u`)** |
| **6** | **Elena-Gabriela Ruse** | 🎾 Tennis (WTA) | `15W – 1L` | **`93.8%`** | `@ 1.29` | `74.3%` | **`+19.5pp`** | **`+20.9%` (`+3.35u`)** |
| **7** | **Carlos Alcaraz** | 🎾 Tennis (ATP) | `83W – 6L` | **`93.3%`** | `@ 1.10` | `87.3%` | **`+5.9pp`** | **`+2.7%` (`+2.38u`)** |
| **8** | **Zielinski, Marcin** | 🏓 Table Tennis (table_tennis) | `12W – 1L` | **`92.3%`** | `@ 1.24` | `79.7%` | **`+12.6pp`** | **`+14.7%` (`+1.91u`)** |
| **9** | **Tereza Valentova** | 🎾 Tennis (WTA) | `21W – 2L` | **`91.3%`** | `@ 1.30` | `73.6%` | **`+17.7pp`** | **`+18.3%` (`+4.21u`)** |
| **10** | **Iva Jovic** | 🎾 Tennis (WTA) | `19W – 2L` | **`90.5%`** | `@ 1.30` | `73.9%` | **`+16.6pp`** | **`+17.4%` (`+3.66u`)** |
| **11** | **Elsa Jacquemot** | 🎾 Tennis (WTA) | `17W – 2L` | **`89.5%`** | `@ 1.32` | `72.4%` | **`+17.0pp`** | **`+18.3%` (`+3.48u`)** |
| **12** | **Sorana Cirstea** | 🎾 Tennis (WTA) | `16W – 2L` | **`88.9%`** | `@ 1.26` | `76.6%` | **`+12.3pp`** | **`+12.6%` (`+2.26u`)** |
| **13** | **Duke Blue Devils** | 🏀 Basketball (ncaam) | `8W – 1L` | **`88.9%`** | `@ 1.23` | `78.7%` | **`+10.2pp`** | **`+6.8%` (`+0.61u`)** |
| **14** | **Warzecha, Miroslaw** | 🏓 Table Tennis (table_tennis) | `15W – 2L` | **`88.2%`** | `@ 1.29` | `77.3%` | **`+11.0pp`** | **`+14.6%` (`+2.49u`)** |
| **15** | **Los Angeles Lakers** | 🏀 Basketball (nba) | `15W – 2L` | **`88.2%`** | `@ 1.30` | `75.1%` | **`+13.1pp`** | **`+12.9%` (`+2.19u`)** |
| **16** | **San Diego Padres** | ⚾ Baseball (mlb) | `7W – 1L` | **`87.5%`** | `@ 1.54` | `62.3%` | **`+25.2pp`** | **`+34.8%` (`+2.78u`)** |
| **17** | **San Francisco 49ers** | 🏈 NFL (nfl) | `7W – 1L` | **`87.5%`** | `@ 1.34` | `72.7%` | **`+14.8pp`** | **`+15.6%` (`+1.25u`)** |
| **18** | **Arizona Wildcats** | 🏀 Basketball (ncaam) | `7W – 1L` | **`87.5%`** | `@ 1.32` | `73.8%` | **`+13.7pp`** | **`+13.9%` (`+1.11u`)** |
| **19** | **Ulrich, Ricardo** | 🎯 Darts (darts) | `7W – 1L` | **`87.5%`** | `@ 1.31` | `75.5%` | **`+12.0pp`** | **`+10.9%` (`+0.87u`)** |
| **20** | **Amanda Anisimova** | 🎾 Tennis (WTA) | `34W – 5L` | **`87.2%`** | `@ 1.22` | `78.8%` | **`+8.4pp`** | **`+6.5%` (`+2.52u`)** |
| **21** | **Naomi Osaka** | 🎾 Tennis (WTA) | `27W – 4L` | **`87.1%`** | `@ 1.25` | `76.5%` | **`+10.6pp`** | **`+9.5%` (`+2.94u`)** |
| **22** | **Katerina Siniakova** | 🎾 Tennis (WTA) | `20W – 3L` | **`87.0%`** | `@ 1.28` | `75.1%` | **`+11.9pp`** | **`+10.5%` (`+2.41u`)** |
| **23** | **Toronto Raptors** | 🏀 Basketball (nba) | `13W – 2L` | **`86.7%`** | `@ 1.39` | `70.5%` | **`+16.2pp`** | **`+20.5%` (`+3.07u`)** |
| **24** | **Tommy Paul** | 🎾 Tennis (ATP) | `43W – 7L` | **`86.0%`** | `@ 1.25` | `76.9%` | **`+9.1pp`** | **`+6.7%` (`+3.33u`)** |
| **25** | **Coco Gauff** | 🎾 Tennis (WTA) | `61W – 10L` | **`85.9%`** | `@ 1.17` | `82.0%` | **`+3.9pp`** | **`+0.3%` (`+0.21u`)** |
| **26** | **Frances Tiafoe** | 🎾 Tennis (ATP) | `18W – 3L` | **`85.7%`** | `@ 1.28` | `74.6%` | **`+11.1pp`** | **`+10.6%` (`+2.23u`)** |
| **27** | **Philadelphia 76ers** | 🏀 Basketball (nba) | `12W – 2L` | **`85.7%`** | `@ 1.32` | `74.1%` | **`+11.6pp`** | **`+10.8%` (`+1.51u`)** |
| **28** | **Pittsburgh Pirates** | ⚾ Baseball (mlb) | `6W – 1L` | **`85.7%`** | `@ 1.57` | `61.0%` | **`+24.7pp`** | **`+34.6%` (`+2.42u`)** |
| **29** | **Elise Mertens** | 🎾 Tennis (WTA) | `29W – 5L` | **`85.3%`** | `@ 1.28` | `74.8%` | **`+10.5pp`** | **`+9.2%` (`+3.14u`)** |
| **30** | **Francesca Jones** | 🎾 Tennis (WTA) | `29W – 5L` | **`85.3%`** | `@ 1.27` | `75.2%` | **`+10.1pp`** | **`+8.1%` (`+2.76u`)** |
| **31** | **Maya Joint** | 🎾 Tennis (WTA) | `23W – 4L` | **`85.2%`** | `@ 1.28` | `75.0%` | **`+10.2pp`** | **`+9.2%` (`+2.49u`)** |
| **32** | **Minnesota Timberwolves** | 🏀 Basketball (nba) | `11W – 2L` | **`84.6%`** | `@ 1.32` | `73.2%` | **`+11.4pp`** | **`+11.0%` (`+1.43u`)** |
| **33** | **Michigan Wolverines** | 🏀 Basketball (ncaam) | `11W – 2L` | **`84.6%`** | `@ 1.24` | `78.4%` | **`+6.3pp`** | **`+2.0%` (`+0.26u`)** |
| **34** | **Alexander Zverev** | 🎾 Tennis (ATP) | `79W – 15L` | **`84.0%`** | `@ 1.18` | `81.5%` | **`+2.6pp`** | **`-1.6%` (`-1.46u`)** |
| **35** | **Alexandra Eala** | 🎾 Tennis (WTA) | `21W – 4L` | **`84.0%`** | `@ 1.25` | `76.7%` | **`+7.3pp`** | **`+5.5%` (`+1.36u`)** |
| **36** | **Learner Tien** | 🎾 Tennis (ATP) | `26W – 5L` | **`83.9%`** | `@ 1.27` | `75.8%` | **`+8.1pp`** | **`+6.0%` (`+1.85u`)** |
| **37** | **Alex de Minaur** | 🎾 Tennis (ATP) | `62W – 12L` | **`83.8%`** | `@ 1.22` | `78.9%` | **`+4.8pp`** | **`+1.2%` (`+0.89u`)** |
| **38** | **Aryna Sabalenka** | 🎾 Tennis (WTA) | `82W – 16L` | **`83.7%`** | `@ 1.14` | `84.4%` | **`-0.7pp`** | **`-5.4%` (`-5.27u`)** |
| **39** | **FC Porto** | ⚽ Football (por.1) | `46W – 9L` | **`83.6%`** | `@ 1.33` | `70.3%` | **`+13.3pp`** | **`+10.1%` (`+5.57u`)** |
| **40** | **Aldridge, Jack** | 🎯 Darts (darts) | `15W – 3L` | **`83.3%`** | `@ 1.43` | `69.6%` | **`+13.7pp`** | **`+16.1%` (`+2.90u`)** |

---

## 2. ⚽ Football (Soccer) — Top 25 Most Reliable Clear Favorites (`<= 1.65` Odds, min 15 matches)

| Rank | Club | League | 1X2 Record (`W–D–L`) | **1X2 Win%** | **1X/X2 Shield%** | Avg Open Odds | Implied Win% | Calibration Edge | 1X2 ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **FC Porto** | `por.1` | `46W–3D–6L` | **`83.6%`** | **`89.1%`** | `@ 1.33` | `70.3%` | **`+13.3pp`** | **`+10.1%` (`+5.57u`)** |
| **2** | **Real Madrid** | `uefa.champions` | `103W–14D–8L` | **`82.4%`** | **`93.6%`** | `@ 1.35` | `70.0%` | **`+12.4pp`** | **`+10.6%` (`+13.22u`)** |
| **3** | **AS Roma** | `ita.1` | `36W–5D–3L` | **`81.8%`** | **`93.2%`** | `@ 1.43` | `65.7%` | **`+16.1pp`** | **`+16.2%` (`+7.13u`)** |
| **4** | **SK Sturm Graz** | `aut.1` | `30W–5D–2L` | **`81.1%`** | **`94.6%`** | `@ 1.44` | `65.6%` | **`+15.5pp`** | **`+17.0%` (`+6.28u`)** |
| **5** | **Real Betis** | `esp.1` | `17W–2D–2L` | **`81.0%`** | **`90.5%`** | `@ 1.47` | `63.6%` | **`+17.3pp`** | **`+19.1%` (`+4.02u`)** |
| **6** | **Stade Rennais** | `uefa.europa` | `29W–4D–3L` | **`80.6%`** | **`91.7%`** | `@ 1.44` | `66.0%` | **`+14.5pp`** | **`+15.5%` (`+5.58u`)** |
| **7** | **Barcelona** | `uefa.champions` | `104W–12D–14L` | **`80.0%`** | **`89.2%`** | `@ 1.34` | `71.0%` | **`+9.0pp`** | **`+5.4%` (`+7.00u`)** |
| **8** | **Aston Villa** | `uefa.champions` | `22W–4D–2L` | **`78.6%`** | **`92.9%`** | `@ 1.46` | `64.6%` | **`+14.0pp`** | **`+13.9%` (`+3.89u`)** |
| **9** | **Atlético Madrid** | `esp.1` | `61W–10D–7L` | **`78.2%`** | **`91.0%`** | `@ 1.40` | `67.4%` | **`+10.8pp`** | **`+8.6%` (`+6.72u`)** |
| **10** | **Sporting CP** | `por.1` | `43W–10D–2L` | **`78.2%`** | **`96.4%`** | `@ 1.26` | `74.1%` | **`+4.1pp`** | **`-2.6%` (`-1.45u`)** |
| **11** | **Internazionale** | `ita.1` | `93W–16D–10L` | **`78.2%`** | **`91.6%`** | `@ 1.35` | `69.7%` | **`+8.5pp`** | **`+4.9%` (`+5.85u`)** |
| **12** | **Benfica** | `por.1` | `42W–9D–3L` | **`77.8%`** | **`94.4%`** | `@ 1.24` | `75.3%` | **`+2.5pp`** | **`-4.4%` (`-2.39u`)** |
| **13** | **Manchester City** | `uefa.champions` | `104W–21D–10L` | **`77.0%`** | **`92.6%`** | `@ 1.32` | `72.0%` | **`+5.0pp`** | **`+0.3%` (`+0.44u`)** |
| **14** | **Tottenham Hotspur** | `eng.1` | `33W–3D–7L` | **`76.7%`** | **`83.7%`** | `@ 1.44` | `65.5%` | **`+11.2pp`** | **`+9.6%` (`+4.13u`)** |
| **15** | **Borussia Dortmund** | `ger.1` | `49W–10D–5L` | **`76.6%`** | **`92.2%`** | `@ 1.40` | `66.7%` | **`+9.8pp`** | **`+7.1%` (`+4.56u`)** |
| **16** | **Arsenal** | `uefa.champions` | `89W–18D–10L` | **`76.1%`** | **`91.5%`** | `@ 1.39` | `68.2%` | **`+7.9pp`** | **`+4.7%` (`+5.48u`)** |
| **17** | **Braga** | `por.1` | `19W–3D–3L` | **`76.0%`** | **`88.0%`** | `@ 1.43` | `65.3%` | **`+10.7pp`** | **`+8.2%` (`+2.05u`)** |
| **18** | **Bayern Munich** | `ger.1` | `118W–24D–15L` | **`75.2%`** | **`90.4%`** | `@ 1.28` | `74.2%` | **`+1.0pp`** | **`-4.7%` (`-7.44u`)** |
| **19** | **Lens** | `fra.1` | `31W–5D–6L` | **`73.8%`** | **`85.7%`** | `@ 1.47` | `64.1%` | **`+9.7pp`** | **`+7.9%` (`+3.30u`)** |
| **20** | **Paris Saint-Germain** | `uefa.champions` | `107W–23D–15L` | **`73.8%`** | **`89.7%`** | `@ 1.33` | `71.4%` | **`+2.4pp`** | **`-2.4%` (`-3.43u`)** |
| **21** | **Bayer Leverkusen** | `uefa.europa` | `52W–12D–7L` | **`73.2%`** | **`90.1%`** | `@ 1.37` | `68.7%` | **`+4.5pp`** | **`-0.7%` (`-0.49u`)** |
| **22** | **Lyon** | `fra.1` | `27W–7D–3L` | **`73.0%`** | **`91.9%`** | `@ 1.44` | `65.7%` | **`+7.3pp`** | **`+3.7%` (`+1.35u`)** |
| **23** | **RB Salzburg** | `aut.1` | `64W–16D–8L` | **`72.7%`** | **`90.9%`** | `@ 1.37` | `69.3%` | **`+3.4pp`** | **`-1.1%` (`-0.93u`)** |
| **24** | **RB Leipzig** | `ger.1` | `50W–13D–6L` | **`72.5%`** | **`91.3%`** | `@ 1.44` | `65.6%` | **`+6.8pp`** | **`+3.7%` (`+2.54u`)** |
| **25** | **Villarreal** | `esp.1` | `26W–2D–8L` | **`72.2%`** | **`77.8%`** | `@ 1.50` | `62.9%` | **`+9.4pp`** | **`+7.3%` (`+2.63u`)** |

---

## 3. 🏀 NBA & Basketball — Top 20 Most Reliable Clear Favorites (`<= 1.65` Odds, min 8 games)

| Rank | Team / Player | League / Tour | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Duke Blue Devils** | `ncaam` | `8W – 1L` | **`88.9%`** | `@ 1.23` | `78.7%` | **`+10.2pp`** | **`+6.8%` (`+0.61u`)** |
| **2** | **Los Angeles Lakers** | `nba` | `15W – 2L` | **`88.2%`** | `@ 1.30` | `75.1%` | **`+13.1pp`** | **`+12.9%` (`+2.19u`)** |
| **3** | **Arizona Wildcats** | `ncaam` | `7W – 1L` | **`87.5%`** | `@ 1.32` | `73.8%` | **`+13.7pp`** | **`+13.9%` (`+1.11u`)** |
| **4** | **Toronto Raptors** | `nba` | `13W – 2L` | **`86.7%`** | `@ 1.39` | `70.5%` | **`+16.2pp`** | **`+20.5%` (`+3.07u`)** |
| **5** | **Philadelphia 76ers** | `nba` | `12W – 2L` | **`85.7%`** | `@ 1.32` | `74.1%` | **`+11.6pp`** | **`+10.8%` (`+1.51u`)** |
| **6** | **Minnesota Timberwolves** | `nba` | `11W – 2L` | **`84.6%`** | `@ 1.32` | `73.2%` | **`+11.4pp`** | **`+11.0%` (`+1.43u`)** |
| **7** | **Michigan Wolverines** | `ncaam` | `11W – 2L` | **`84.6%`** | `@ 1.24` | `78.4%` | **`+6.3pp`** | **`+2.0%` (`+0.26u`)** |
| **8** | **Portland Trail Blazers** | `nba` | `15W – 3L` | **`83.3%`** | `@ 1.31` | `74.4%` | **`+8.9pp`** | **`+8.7%` (`+1.57u`)** |
| **9** | **Cleveland Cavaliers** | `nba` | `23W – 5L` | **`82.1%`** | `@ 1.32` | `74.2%` | **`+7.9pp`** | **`+5.6%` (`+1.57u`)** |
| **10** | **LA Clippers** | `nba` | `13W – 3L` | **`81.2%`** | `@ 1.32` | `73.9%` | **`+7.3pp`** | **`+5.6%` (`+0.89u`)** |
| **11** | **Denver Nuggets** | `nba` | `17W – 4L` | **`81.0%`** | `@ 1.31` | `74.5%` | **`+6.4pp`** | **`+4.5%` (`+0.94u`)** |
| **12** | **Orlando Magic** | `nba` | `8W – 2L` | **`80.0%`** | `@ 1.28` | `76.8%` | **`+3.2pp`** | **`+0.3%` (`+0.03u`)** |
| **13** | **Oklahoma City Thunder** | `nba` | `27W – 7L` | **`79.4%`** | `@ 1.30` | `75.1%` | **`+4.4pp`** | **`-0.2%` (`-0.06u`)** |
| **14** | **New York Knicks** | `nba` | `19W – 5L` | **`79.2%`** | `@ 1.36` | `71.9%` | **`+7.3pp`** | **`+5.3%` (`+1.26u`)** |
| **15** | **Detroit Pistons** | `nba` | `19W – 5L` | **`79.2%`** | `@ 1.35` | `72.9%` | **`+6.2pp`** | **`+4.5%` (`+1.07u`)** |
| **16** | **Boston Celtics** | `nba` | `21W – 6L` | **`77.8%`** | `@ 1.27` | `76.2%` | **`+1.5pp`** | **`-1.5%` (`-0.40u`)** |
| **17** | **Charlotte Hornets** | `nba` | `14W – 4L` | **`77.8%`** | `@ 1.38` | `71.1%` | **`+6.7pp`** | **`+4.9%` (`+0.89u`)** |
| **18** | **Atlanta Hawks** | `nba` | `14W – 4L` | **`77.8%`** | `@ 1.36` | `71.6%` | **`+6.2pp`** | **`+1.4%` (`+0.25u`)** |
| **19** | **Miami Heat** | `nba` | `9W – 3L` | **`75.0%`** | `@ 1.29` | `76.4%` | **`-1.4pp`** | **`-6.6%` (`-0.79u`)** |
| **20** | **Purdue Boilermakers** | `ncaam` | `6W – 2L` | **`75.0%`** | `@ 1.31` | `73.6%` | **`+1.4pp`** | **`-2.0%` (`-0.16u`)** |

---

## 4. 🏒 NHL Hockey — Most Reliable Clear Favorites (`<= 1.65` Odds, min 6 games)

| Rank | Team / Player | League / Tour | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **New Jersey Devils** | `nhl` | `6W – 1L` | **`85.7%`** | `@ 1.54` | `62.3%` | **`+23.4pp`** | **`+32.0%` (`+2.24u`)** |
| **2** | **Ottawa Senators** | `nhl` | `9W – 2L` | **`81.8%`** | `@ 1.53` | `62.9%` | **`+18.9pp`** | **`+23.6%` (`+2.60u`)** |
| **3** | **Vegas Golden Knights** | `nhl` | `19W – 6L` | **`76.0%`** | `@ 1.54` | `62.8%` | **`+13.2pp`** | **`+14.5%` (`+3.63u`)** |
| **4** | **Carolina Hurricanes** | `nhl` | `24W – 8L` | **`75.0%`** | `@ 1.50` | `64.0%` | **`+11.0pp`** | **`+12.0%` (`+3.85u`)** |
| **5** | **New York Islanders** | `nhl` | `6W – 2L` | **`75.0%`** | `@ 1.54` | `62.6%` | **`+12.4pp`** | **`+14.8%` (`+1.18u`)** |
| **6** | **Dallas Stars** | `nhl` | `13W – 5L` | **`72.2%`** | `@ 1.54` | `62.3%` | **`+9.9pp`** | **`+9.9%` (`+1.78u`)** |
| **7** | **Los Angeles Kings** | `nhl` | `5W – 2L` | **`71.4%`** | `@ 1.56` | `61.8%` | **`+9.6pp`** | **`+10.5%` (`+0.74u`)** |
| **8** | **Colorado Avalanche** | `nhl` | `26W – 13L` | **`66.7%`** | `@ 1.49` | `64.5%` | **`+2.1pp`** | **`-0.2%` (`-0.10u`)** |
| **9** | **Edmonton Oilers** | `nhl` | `10W – 5L` | **`66.7%`** | `@ 1.51` | `63.8%` | **`+2.9pp`** | **`-0.2%` (`-0.03u`)** |
| **10** | **Boston Bruins** | `nhl` | `4W – 2L` | **`66.7%`** | `@ 1.57` | `61.4%` | **`+5.3pp`** | **`+4.1%` (`+0.25u`)** |
| **11** | **Florida Panthers** | `nhl` | `4W – 2L` | **`66.7%`** | `@ 1.52` | `63.4%` | **`+3.2pp`** | **`-1.8%` (`-0.11u`)** |
| **12** | **Tampa Bay Lightning** | `nhl` | `17W – 11L` | **`60.7%`** | `@ 1.51` | `63.8%` | **`-3.1pp`** | **`-9.2%` (`-2.58u`)** |
| **13** | **Montreal Canadiens** | `nhl` | `6W – 4L` | **`60.0%`** | `@ 1.55` | `62.0%` | **`-2.0pp`** | **`-6.6%` (`-0.66u`)** |
| **14** | **Minnesota Wild** | `nhl` | `10W – 7L` | **`58.8%`** | `@ 1.50` | `64.3%` | **`-5.5pp`** | **`-9.6%` (`-1.63u`)** |
| **15** | **Buffalo Sabres** | `nhl` | `8W – 6L` | **`57.1%`** | `@ 1.55` | `62.0%` | **`-4.8pp`** | **`-12.9%` (`-1.81u`)** |
| **16** | **Utah Mammoth** | `nhl` | `6W – 8L` | **`42.9%`** | `@ 1.55` | `62.0%` | **`-19.2pp`** | **`-33.8%` (`-4.74u`)** |
| **17** | **Anaheim Ducks** | `nhl` | `3W – 8L` | **`27.3%`** | `@ 1.55` | `62.1%` | **`-34.8pp`** | **`-57.3%` (`-6.31u`)** |

---

## 5. 🏈 NFL American Football — Most Reliable Clear Favorites (`<= 1.65` Odds, min 6 games)

| Rank | Team / Player | League / Tour | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **New England Patriots** | `nfl` | `10W – 0L` | **`100.0%`** | `@ 1.34` | `72.5%` | **`+27.5pp`** | **`+34.0%` (`+3.40u`)** |
| **2** | **San Francisco 49ers** | `nfl` | `7W – 1L` | **`87.5%`** | `@ 1.34` | `72.7%` | **`+14.8pp`** | **`+15.6%` (`+1.25u`)** |
| **3** | **Cincinnati Bengals** | `nfl` | `5W – 1L` | **`83.3%`** | `@ 1.42` | `67.6%` | **`+15.8pp`** | **`+20.6%` (`+1.24u`)** |
| **4** | **Green Bay Packers** | `nfl` | `5W – 2L` | **`71.4%`** | `@ 1.44` | `67.4%` | **`+4.0pp`** | **`+2.4%` (`+0.17u`)** |
| **5** | **Buffalo Bills** | `nfl` | `5W – 2L` | **`71.4%`** | `@ 1.40` | `69.4%` | **`+2.0pp`** | **`-5.7%` (`-0.40u`)** |
| **6** | **Seattle Seahawks** | `nfl` | `8W – 4L` | **`66.7%`** | `@ 1.45` | `67.0%` | **`-0.3pp`** | **`-6.0%` (`-0.72u`)** |
| **7** | **Detroit Lions** | `nfl` | `5W – 3L` | **`62.5%`** | `@ 1.40` | `69.0%` | **`-6.5pp`** | **`-16.4%` (`-1.31u`)** |
| **8** | **Los Angeles Rams** | `nfl` | `8W – 5L` | **`61.5%`** | `@ 1.35` | `72.5%` | **`-11.0pp`** | **`-18.0%` (`-2.33u`)** |
| **9** | **Kansas City Chiefs** | `nfl` | `4W – 4L` | **`50.0%`** | `@ 1.40` | `69.3%` | **`-19.3pp`** | **`-28.4%` (`-2.27u`)** |
| **10** | **Philadelphia Eagles** | `nfl` | `4W – 4L` | **`50.0%`** | `@ 1.40` | `69.5%` | **`-19.5pp`** | **`-32.9%` (`-2.63u`)** |
| **11** | **Baltimore Ravens** | `nfl` | `4W – 5L` | **`44.4%`** | `@ 1.44` | `67.2%` | **`-22.7pp`** | **`-34.5%` (`-3.10u`)** |
| **12** | **Dallas Cowboys** | `nfl` | `2W – 4L` | **`33.3%`** | `@ 1.41` | `68.6%` | **`-35.3pp`** | **`-48.2%` (`-2.89u`)** |
| **13** | **Tampa Bay Buccaneers** | `nfl` | `2W – 4L` | **`33.3%`** | `@ 1.44` | `67.0%` | **`-33.7pp`** | **`-50.6%` (`-3.03u`)** |

---

## 6. ⚾ MLB & International Baseball — Most Reliable Clear Favorites (`<= 1.65` Odds, min 6 games)

| Rank | Team / Player | League / Tour | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **San Diego Padres** | `mlb` | `7W – 1L` | **`87.5%`** | `@ 1.54` | `62.3%` | **`+25.2pp`** | **`+34.8%` (`+2.78u`)** |
| **2** | **Pittsburgh Pirates** | `mlb` | `6W – 1L` | **`85.7%`** | `@ 1.57` | `61.0%` | **`+24.7pp`** | **`+34.6%` (`+2.42u`)** |
| **3** | **Caribes de Anzoategu** | `baseball` | `5W – 1L` | **`83.3%`** | `@ 1.49` | `66.4%` | **`+17.0pp`** | **`+24.5%` (`+1.47u`)** |
| **4** | **Milwaukee Brewers** | `mlb` | `18W – 5L` | **`78.3%`** | `@ 1.54` | `62.1%` | **`+16.1pp`** | **`+19.9%` (`+4.57u`)** |
| **5** | **Boston Red Sox** | `mlb` | `10W – 3L` | **`76.9%`** | `@ 1.55` | `62.0%` | **`+14.9pp`** | **`+19.6%` (`+2.55u`)** |
| **6** | **New York Yankees** | `mlb` | `10W – 3L` | **`76.9%`** | `@ 1.51` | `63.7%` | **`+13.2pp`** | **`+14.4%` (`+1.87u`)** |
| **7** | **Philadelphia Phillies** | `mlb` | `10W – 4L` | **`71.4%`** | `@ 1.56` | `61.5%` | **`+9.9pp`** | **`+10.4%` (`+1.46u`)** |
| **8** | **Vegueros Pinar** | `baseball` | `5W – 2L` | **`71.4%`** | `@ 1.49` | `65.9%` | **`+5.5pp`** | **`+5.1%` (`+0.36u`)** |
| **9** | **Cleveland Guardians** | `mlb` | `11W – 5L` | **`68.8%`** | `@ 1.58` | `60.6%` | **`+8.1pp`** | **`+7.8%` (`+1.24u`)** |
| **10** | **Los Angeles Dodgers** | `mlb` | `23W – 12L` | **`65.7%`** | `@ 1.48` | `65.2%` | **`+0.6pp`** | **`-5.5%` (`-1.92u`)** |
| **11** | **Atlanta Braves** | `mlb` | `7W – 4L` | **`63.6%`** | `@ 1.50` | `63.8%` | **`-0.2pp`** | **`-5.5%` (`-0.60u`)** |
| **12** | **Tampa Bay Rays** | `mlb` | `8W – 5L` | **`61.5%`** | `@ 1.55` | `62.0%` | **`-0.5pp`** | **`-6.4%` (`-0.84u`)** |
| **13** | **Detroit Tigers** | `mlb` | `4W – 3L` | **`57.1%`** | `@ 1.61` | `59.4%` | **`-2.3pp`** | **`-7.8%` (`-0.55u`)** |
| **14** | **Chicago Cubs** | `mlb` | `6W – 5L` | **`54.5%`** | `@ 1.55` | `61.9%` | **`-7.3pp`** | **`-15.4%` (`-1.70u`)** |
| **15** | **Leones Industriales** | `baseball` | `3W – 3L` | **`50.0%`** | `@ 1.55` | `63.2%` | **`-13.2pp`** | **`-21.8%` (`-1.31u`)** |
| **16** | **Houston Astros** | `mlb` | `3W – 4L` | **`42.9%`** | `@ 1.56` | `61.4%` | **`-18.5pp`** | **`-32.4%` (`-2.26u`)** |
| **17** | **Seattle Mariners** | `mlb` | `3W – 6L` | **`33.3%`** | `@ 1.52` | `62.9%` | **`-29.6pp`** | **`-47.9%` (`-4.31u`)** |
| **18** | **Aguilas Mexicali** | `baseball` | `2W – 4L` | **`33.3%`** | `@ 1.57` | `62.6%` | **`-29.3pp`** | **`-46.8%` (`-2.81u`)** |

---

## 7. 🏓 Table Tennis — Top 15 Most Reliable Clear Favorites (`<= 1.65` Odds, min 10 matches)

| Rank | Team / Player | League / Tour | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Zielinski, Marcin** | `table_tennis` | `12W – 1L` | **`92.3%`** | `@ 1.24` | `79.7%` | **`+12.6pp`** | **`+14.7%` (`+1.91u`)** |
| **2** | **Warzecha, Miroslaw** | `table_tennis` | `15W – 2L` | **`88.2%`** | `@ 1.29` | `77.3%` | **`+11.0pp`** | **`+14.6%` (`+2.49u`)** |
| **3** | **Pietraszko, Lukasz** | `table_tennis` | `10W – 2L` | **`83.3%`** | `@ 1.51` | `65.2%` | **`+18.2pp`** | **`+26.7%` (`+3.20u`)** |
| **4** | **Zmijewski, Artur** | `table_tennis` | `13W – 3L` | **`81.2%`** | `@ 1.37` | `72.4%` | **`+8.9pp`** | **`+9.3%` (`+1.48u`)** |
| **5** | **Hetnar, Krzysztof** | `table_tennis` | `17W – 4L` | **`81.0%`** | `@ 1.44` | `69.1%` | **`+11.9pp`** | **`+17.4%` (`+3.66u`)** |
| **6** | **Staszczyk, Konrad** | `table_tennis` | `11W – 3L` | **`78.6%`** | `@ 1.41` | `70.4%` | **`+8.1pp`** | **`+7.8%` (`+1.09u`)** |
| **7** | **Michalik, Jerzy** | `table_tennis` | `10W – 3L` | **`76.9%`** | `@ 1.35` | `73.6%` | **`+3.3pp`** | **`+2.8%` (`+0.37u`)** |
| **8** | **Kiejda, Patryk** | `table_tennis` | `10W – 4L` | **`71.4%`** | `@ 1.48` | `66.4%` | **`+5.0pp`** | **`+7.9%` (`+1.11u`)** |
| **9** | **Nocun, Zbigniew** | `table_tennis` | `10W – 4L` | **`71.4%`** | `@ 1.40` | `70.7%` | **`+0.7pp`** | **`-0.6%` (`-0.09u`)** |
| **10** | **David, Petr** | `table_tennis` | `7W – 3L` | **`70.0%`** | `@ 1.47` | `67.4%` | **`+2.6pp`** | **`+1.8%` (`+0.18u`)** |
| **11** | **Jadach, Oskar** | `table_tennis` | `11W – 7L` | **`61.1%`** | `@ 1.44` | `69.0%` | **`-7.9pp`** | **`-15.3%` (`-2.76u`)** |
| **12** | **Oracz, Jacek** | `table_tennis` | `11W – 7L` | **`61.1%`** | `@ 1.37` | `72.1%` | **`-11.0pp`** | **`-19.5%` (`-3.51u`)** |
| **13** | **Wiekiera, Arkadiusz** | `table_tennis` | `6W – 4L` | **`60.0%`** | `@ 1.54` | `63.8%` | **`-3.8pp`** | **`-7.7%` (`-0.77u`)** |
| **14** | **Stepien, Marcin** | `table_tennis` | `6W – 4L` | **`60.0%`** | `@ 1.53` | `64.3%` | **`-4.3pp`** | **`-8.1%` (`-0.81u`)** |
| **15** | **Poliniewicz, Grzegorz** | `table_tennis` | `6W – 4L` | **`60.0%`** | `@ 1.45` | `67.9%` | **`-7.9pp`** | **`-15.9%` (`-1.59u`)** |
| **16** | **Tkocz, Marek** | `table_tennis` | `6W – 4L` | **`60.0%`** | `@ 1.43` | `69.0%` | **`-9.0pp`** | **`-16.7%` (`-1.67u`)** |
| **17** | **Ovcharenko, Maksim** | `table_tennis` | `10W – 7L` | **`58.8%`** | `@ 1.51` | `65.1%` | **`-6.3pp`** | **`-11.5%` (`-1.96u`)** |
| **18** | **Fomin, Andriej** | `table_tennis` | `6W – 5L` | **`54.5%`** | `@ 1.42` | `69.8%` | **`-15.2pp`** | **`-25.6%` (`-2.82u`)** |
| **19** | **Slawinski, Kacper** | `table_tennis` | `7W – 6L` | **`53.8%`** | `@ 1.42` | `69.2%` | **`-15.3pp`** | **`-23.8%` (`-3.10u`)** |
| **20** | **Kubiak, Artur** | `table_tennis` | `7W – 6L` | **`53.8%`** | `@ 1.38` | `71.6%` | **`-17.8pp`** | **`-26.7%` (`-3.47u`)** |

---

## 8. 🎾 ATP & WTA Tennis — Top 30 Most Reliable Clear Favorites (`2025–2026`, min 15 matches)

| Rank | Team / Player | League / Tour | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | Calibration Edge | Flat-Stake ROI (`PnL`) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Marie Bouzkova** | `WTA` | `21W – 1L` | **`95.5%`** | `@ 1.27` | `75.5%` | **`+20.0pp`** | **`+21.2%` (`+4.66u`)** |
| **2** | **Ashlyn Krueger** | `WTA` | `19W – 1L` | **`95.0%`** | `@ 1.30` | `73.6%` | **`+21.4pp`** | **`+23.2%` (`+4.64u`)** |
| **3** | **Jannik Sinner** | `ATP` | `75W – 5L` | **`93.8%`** | `@ 1.07` | `89.9%` | **`+3.9pp`** | **`-0.1%` (`-0.05u`)** |
| **4** | **Elena-Gabriela Ruse** | `WTA` | `15W – 1L` | **`93.8%`** | `@ 1.29` | `74.3%` | **`+19.5pp`** | **`+20.9%` (`+3.35u`)** |
| **5** | **Carlos Alcaraz** | `ATP` | `83W – 6L` | **`93.3%`** | `@ 1.10` | `87.3%` | **`+5.9pp`** | **`+2.7%` (`+2.38u`)** |
| **6** | **Tereza Valentova** | `WTA` | `21W – 2L` | **`91.3%`** | `@ 1.30` | `73.6%` | **`+17.7pp`** | **`+18.3%` (`+4.21u`)** |
| **7** | **Iva Jovic** | `WTA` | `19W – 2L` | **`90.5%`** | `@ 1.30` | `73.9%` | **`+16.6pp`** | **`+17.4%` (`+3.66u`)** |
| **8** | **Elsa Jacquemot** | `WTA` | `17W – 2L` | **`89.5%`** | `@ 1.32` | `72.4%` | **`+17.0pp`** | **`+18.3%` (`+3.48u`)** |
| **9** | **Sorana Cirstea** | `WTA` | `16W – 2L` | **`88.9%`** | `@ 1.26` | `76.6%` | **`+12.3pp`** | **`+12.6%` (`+2.26u`)** |
| **10** | **Amanda Anisimova** | `WTA` | `34W – 5L` | **`87.2%`** | `@ 1.22` | `78.8%` | **`+8.4pp`** | **`+6.5%` (`+2.52u`)** |
| **11** | **Naomi Osaka** | `WTA` | `27W – 4L` | **`87.1%`** | `@ 1.25` | `76.5%` | **`+10.6pp`** | **`+9.5%` (`+2.94u`)** |
| **12** | **Katerina Siniakova** | `WTA` | `20W – 3L` | **`87.0%`** | `@ 1.28` | `75.1%` | **`+11.9pp`** | **`+10.5%` (`+2.41u`)** |
| **13** | **Tommy Paul** | `ATP` | `43W – 7L` | **`86.0%`** | `@ 1.25` | `76.9%` | **`+9.1pp`** | **`+6.7%` (`+3.33u`)** |
| **14** | **Coco Gauff** | `WTA` | `61W – 10L` | **`85.9%`** | `@ 1.17` | `82.0%` | **`+3.9pp`** | **`+0.3%` (`+0.21u`)** |
| **15** | **Frances Tiafoe** | `ATP` | `18W – 3L` | **`85.7%`** | `@ 1.28` | `74.6%` | **`+11.1pp`** | **`+10.6%` (`+2.23u`)** |
| **16** | **Elise Mertens** | `WTA` | `29W – 5L` | **`85.3%`** | `@ 1.28` | `74.8%` | **`+10.5pp`** | **`+9.2%` (`+3.14u`)** |
| **17** | **Francesca Jones** | `WTA` | `29W – 5L` | **`85.3%`** | `@ 1.27` | `75.2%` | **`+10.1pp`** | **`+8.1%` (`+2.76u`)** |
| **18** | **Maya Joint** | `WTA` | `23W – 4L` | **`85.2%`** | `@ 1.28` | `75.0%` | **`+10.2pp`** | **`+9.2%` (`+2.49u`)** |
| **19** | **Alexander Zverev** | `ATP` | `79W – 15L` | **`84.0%`** | `@ 1.18` | `81.5%` | **`+2.6pp`** | **`-1.6%` (`-1.46u`)** |
| **20** | **Alexandra Eala** | `WTA` | `21W – 4L` | **`84.0%`** | `@ 1.25` | `76.7%` | **`+7.3pp`** | **`+5.5%` (`+1.36u`)** |
| **21** | **Learner Tien** | `ATP` | `26W – 5L` | **`83.9%`** | `@ 1.27` | `75.8%` | **`+8.1pp`** | **`+6.0%` (`+1.85u`)** |
| **22** | **Alex de Minaur** | `ATP` | `62W – 12L` | **`83.8%`** | `@ 1.22` | `78.9%` | **`+4.8pp`** | **`+1.2%` (`+0.89u`)** |
| **23** | **Aryna Sabalenka** | `WTA` | `82W – 16L` | **`83.7%`** | `@ 1.14` | `84.4%` | **`-0.7pp`** | **`-5.4%` (`-5.27u`)** |
| **24** | **Leylah Fernandez** | `WTA` | `15W – 3L` | **`83.3%`** | `@ 1.30` | `73.7%` | **`+9.6pp`** | **`+7.9%` (`+1.43u`)** |
| **25** | **Iga Swiatek** | `WTA` | `81W – 17L` | **`82.7%`** | `@ 1.16` | `83.2%` | **`-0.5pp`** | **`-5.4%` (`-5.25u`)** |
| **26** | **Elena Rybakina** | `WTA` | `61W – 13L` | **`82.4%`** | `@ 1.18` | `81.6%` | **`+0.9pp`** | **`-3.1%` (`-2.26u`)** |
| **27** | **Aliaksandra Sasnovich** | `WTA` | `14W – 3L` | **`82.4%`** | `@ 1.30` | `73.4%` | **`+9.0pp`** | **`+7.6%` (`+1.28u`)** |
| **28** | **Taylor Fritz** | `ATP` | `60W – 13L` | **`82.2%`** | `@ 1.21` | `79.4%` | **`+2.8pp`** | **`-1.2%` (`-0.87u`)** |
| **29** | **Sara Bejlek** | `WTA` | `23W – 5L` | **`82.1%`** | `@ 1.28` | `74.7%` | **`+7.5pp`** | **`+5.8%` (`+1.62u`)** |
| **30** | **Viktorija Golubic** | `WTA` | `23W – 5L` | **`82.1%`** | `@ 1.28` | `74.8%` | **`+7.4pp`** | **`+5.2%` (`+1.46u`)** |

---

## 9. ⚠️ Chronically Overestimated "Paper-Tiger" Favorites (Lowest Accuracy vs. Opening Odds)

These teams and players repeatedly fail to cover their opening favorite odds (`Calibration Edge <= -8.0pp`) and are prime targets for BetScout's **`Fade Traps` (`fade_trap`)** filter:

| Rank | Team / Player | Sport & Competition | Fav Record (`W–L`) | **Win Accuracy %** | Avg Open Odds | Implied Win% | **Underperformance Gap** | Flat-Stake Fav ROI |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **Badura, Jaroslaw** | 🏓 Table Tennis (table_tennis) | `3W – 7L` | **`30.0%`** | `@ 1.48` | `66.4%` | **`-36.4pp`** | **`-56.3%` (`-5.63u`)** |
| **2** | **Dallas Cowboys** | 🏈 NFL (nfl) | `2W – 4L` | **`33.3%`** | `@ 1.41` | `68.6%` | **`-35.3pp`** | **`-48.2%` (`-2.89u`)** |
| **3** | **Anaheim Ducks** | 🏒 NHL Hockey (nhl) | `3W – 8L` | **`27.3%`** | `@ 1.55` | `62.1%` | **`-34.8pp`** | **`-57.3%` (`-6.31u`)** |
| **4** | **Tampa Bay Buccaneers** | 🏈 NFL (nfl) | `2W – 4L` | **`33.3%`** | `@ 1.44` | `67.0%` | **`-33.7pp`** | **`-50.6%` (`-3.03u`)** |
| **5** | **Seattle Mariners** | ⚾ Baseball (mlb) | `3W – 6L` | **`33.3%`** | `@ 1.52` | `62.9%` | **`-29.6pp`** | **`-47.9%` (`-4.31u`)** |
| **6** | **Aguilas Mexicali** | ⚾ Baseball (baseball) | `2W – 4L` | **`33.3%`** | `@ 1.57` | `62.6%` | **`-29.3pp`** | **`-46.8%` (`-2.81u`)** |
| **7** | **Tkaczyk, Henryk** | 🏓 Table Tennis (table_tennis) | `5W – 8L` | **`38.5%`** | `@ 1.47` | `67.2%` | **`-28.7pp`** | **`-45.9%` (`-5.97u`)** |
| **8** | **Brighton & Hove Albion** | ⚽ Football (uefa.europa.conf) | `12W – 17L` | **`41.4%`** | `@ 1.45` | `65.4%` | **`-24.0pp`** | **`-40.5%` (`-11.73u`)** |
| **9** | **Lamperski, Jakub** | 🏓 Table Tennis (table_tennis) | `6W – 7L` | **`46.2%`** | `@ 1.42` | `69.5%` | **`-23.4pp`** | **`-36.0%` (`-4.68u`)** |
| **10** | **Baltimore Ravens** | 🏈 NFL (nfl) | `4W – 5L` | **`44.4%`** | `@ 1.44` | `67.2%` | **`-22.7pp`** | **`-34.5%` (`-3.10u`)** |
| **11** | **Philadelphia Eagles** | 🏈 NFL (nfl) | `4W – 4L` | **`50.0%`** | `@ 1.40` | `69.5%` | **`-19.5pp`** | **`-32.9%` (`-2.63u`)** |
| **12** | **Kansas City Chiefs** | 🏈 NFL (nfl) | `4W – 4L` | **`50.0%`** | `@ 1.40` | `69.3%` | **`-19.3pp`** | **`-28.4%` (`-2.27u`)** |
| **13** | **Utah Mammoth** | 🏒 NHL Hockey (nhl) | `6W – 8L` | **`42.9%`** | `@ 1.55` | `62.0%` | **`-19.2pp`** | **`-33.8%` (`-4.74u`)** |
| **14** | **Kolek, Maciej** | 🏓 Table Tennis (table_tennis) | `6W – 6L` | **`50.0%`** | `@ 1.44` | `68.6%` | **`-18.6pp`** | **`-29.3%` (`-3.52u`)** |
| **15** | **Lebek, Marian** | 🏓 Table Tennis (table_tennis) | `5W – 5L` | **`50.0%`** | `@ 1.44` | `68.5%` | **`-18.5pp`** | **`-29.4%` (`-2.94u`)** |
| **16** | **Houston Astros** | ⚾ Baseball (mlb) | `3W – 4L` | **`42.9%`** | `@ 1.56` | `61.4%` | **`-18.5pp`** | **`-32.4%` (`-2.26u`)** |
| **17** | **Kubiak, Artur** | 🏓 Table Tennis (table_tennis) | `7W – 6L` | **`53.8%`** | `@ 1.38` | `71.6%` | **`-17.8pp`** | **`-26.7%` (`-3.47u`)** |
| **18** | **Pruszkowski, Jakub** | 🏓 Table Tennis (table_tennis) | `8W – 8L` | **`50.0%`** | `@ 1.46` | `67.5%` | **`-17.5pp`** | **`-28.6%` (`-4.58u`)** |
| **19** | **Golden State Warriors** | 🏀 Basketball (nba) | `6W – 5L` | **`54.5%`** | `@ 1.36` | `71.7%` | **`-17.2pp`** | **`-30.2%` (`-3.32u`)** |
| **20** | **Simona Waltert** | 🎾 Tennis (WTA) | `9W – 6L` | **`60.0%`** | `@ 1.25` | `76.5%` | **`-16.5pp`** | **`-25.8%` (`-3.88u`)** |
| **21** | **Holger Rune** | 🎾 Tennis (ATP) | `20W – 14L` | **`58.8%`** | `@ 1.28` | `75.2%` | **`-16.4pp`** | **`-24.8%` (`-8.42u`)** |
| **22** | **Usher, Graham** | 🎯 Darts (darts) | `4W – 3L` | **`57.1%`** | `@ 1.37` | `73.0%` | **`-15.8pp`** | **`-29.0%` (`-2.03u`)** |
| **23** | **Grigor Dimitrov** | 🎾 Tennis (ATP) | `16W – 10L` | **`61.5%`** | `@ 1.25` | `77.0%` | **`-15.5pp`** | **`-24.8%` (`-6.44u`)** |
| **24** | **Slawinski, Kacper** | 🏓 Table Tennis (table_tennis) | `7W – 6L` | **`53.8%`** | `@ 1.42` | `69.2%` | **`-15.3pp`** | **`-23.8%` (`-3.10u`)** |
| **25** | **Fomin, Andriej** | 🏓 Table Tennis (table_tennis) | `6W – 5L` | **`54.5%`** | `@ 1.42` | `69.8%` | **`-15.2pp`** | **`-25.6%` (`-2.82u`)** |

---

## 10. 🚀 Combining Proven-Accuracy Favorites into `2x` & `3x` Combos (`<= 48h` Window)

A zero-lookahead walk-forward backtest on post-July 2025 matches (`>= 2025-07-01`) reveals a critical distinction when building `2x` and `3x` combos within a `<= 48-hour` (1–2 day) window:

1. **Why Raw Favorites Alone Are Not Enough:** Pairing any favorite with a high historical win rate *without* checking current rolling boxscore dominance (SoT / Game-Share) yields `60.7%` WR (`-1.7%` ROI) on `2x` combos because bookmaker vigorish compounds across legs.
2. **Why Model-Gated + Proven-Accuracy Favorites Multiply ROI by `4.7x–6.7x`:** When each leg is **both** a proven historical favorite (`Win% >= 76%–82%`, `Calibration Edge >= +5.0pp`) **and** passes BetScout's positive rolling boxscore gate (`SoT diff >= +1.5/gm` in Football, `+0.5` in US Sports, or `Game-Share >= +5.5%` & `6m Form >= +20%` in Tennis), each leg carries positive true Expected Value (`E[R_i] = p_i × O_i > 1.0`). Multiplying 2 or 3 independent positive-EV legs within a `<= 48h` window compounds the edge multiplicatively:

| Strategy (`>= 2025-07-01` Out-of-Sample, Zero Lookahead) | Settled Tickets (`W–L`) | **Realized Win Rate** | Avg Combined Odds | Total Net Profit (`1u` flat) | **Return on Investment (`ROI%`)** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. Single Legs (Model-Gated + Proven Favorite)** | `290W – 81L` (`n = 371`) | **`78.2%`** | `@ 1.33` | `+9.61u` | **`+2.6%`** |
| **2. `2x` Proven-Accuracy Double (`<= 48h` Window)** | **`110W – 59L` (`n = 169`)** | **`65.1%`** | **`@ 1.79x`** | **`+20.71u`** | **`+12.3%` (`4.7×` Singles ROI)** |
| **3. `3x` Proven-Accuracy Treble (`<= 48h` Window)** | **`46W – 42L` (`n = 88`)** | **`52.3%`** | **`@ 2.41x`** | **`+15.33u`** | **`+17.4%` (`6.7×` Singles ROI)** |

### How BetScout Automates This in the App (`Tab 2: Combos & Dutching Studio`)
- **`⚡ 2x Proven-Accuracy Banker Double (≤48h)` & `🚀 3x Proven-Accuracy Banker Treble (≤48h)`:** Automatically prioritizes legs with a verified `Fav XW-YL` badge (`fav_reliability`) and groups them within a **48-hour (`1–2 day`) kickoff window** so your bankroll turns over quickly and you can use the **Combo Saver DIY Hedge Calculator** if the final leg kicks off the next day.
- **`Top 90+ Combo` 1-Click Builder:** Clicking **`Top 90+ Combo`** automatically selects the highest-scoring (`88+/100` Edge Score) proven-accuracy legs from distinct matches within a `<= 48h` window.

