extensions [array]

globals [

  ;; ===== 场景与人口 =====
  retirement-age
  pension-system
  household-count
  firm-count
  max-lifespan
  contract-duration
  youth-age-limit
  birth-rate-shift    ;;

  ;; ===== 初始化参数 =====
  kappa
  phi
  ini-price
  ini-wage
  ini-productivity
  ini-production
  ini-savings
  initial-inventory-ratio
  initial-young-unemp
  initial-old-unemp
  buffer-periods
  reserve-years

  ;; ===== 场景行为参数 =====
  reorg-prob
  consumer-choice
  job-application
  wealth-consumption-cap

  ;; ===== 税率与利率 =====
  tau-w
  tau-pi
  savings-return-rate
  policy-rates

  ;; ===== 运行时长控制（新增：区分"历史校准"与"长程理论验证"两种模式） =====
  max-ticks

  ;; ===== production-target 上限倍数（新增，可在界面调节，见target-cap-multiplier输入框） =====
  ;target-cap-multiplier

  ;; ===== 时间序列数据（外生输入） =====
  productivity-growth-rates
  wage-increase-rates
  deposit-rates
  lend-rates
  paygo-rates
  pension-annual-returns
  age-distributions
  death-prob
  birth-rates-list

  ;; ===== 真实数据（用于plot对比） =====
  real-rgdp-growth
  real-unemp
  real-young-unemp
  real-old-unemp
  real-pension-growth
  real-inflation

  ;; ===== 市场价格与CPI =====
  mpc-income-baseline
  mpc-wealth-baseline
  market-price
  previous-market-price
  base-price
  cpi
  previous-cpi
  inflation
  price-adjustment


  ;; ===== GDP =====
  nominal-gdp
  real-gdp
  previous-real-gdp
  gdp-growth


  ;; ===== 劳动力市场 =====
  total-workers
  average-wage
  avg-income
  young-unemployment
  old-unemployment
  total-unemployment
  avg-young-unemployment
  avg-old-unemployment
  total-vacancies
  vacancy-rate
  previous-unemployment
  delta-unemployment

  ;; ===== 当前金融状态与财政 =====
  credit-threshold
  default-tolerance
  bankruptcies-this-tick
  loan-index
  initial-total-loans

  ;; ===== 养老金 =====
  pension-growth
  annual-pension-growth
  previous-year-pension-balance
  pension-contributions
  pension-benefits
  pension-balance-history

  ;; ===== 其他 =====
  total-demand
  tracked-firm

  ;; ===== death =====
  deaths-15-19  deaths-20-24  deaths-25-29  deaths-30-34
  deaths-35-39  deaths-40-44  deaths-45-49  deaths-50-54
  deaths-55-59  deaths-60-64  deaths-65-69  deaths-70-74
  deaths-75-79  deaths-80-84  deaths-85-89  deaths-90-94
  deaths-95-99  deaths-100plus

]

breed [households household]
breed [firms firm]
breed [banks bank]
breed [governments government]

households-own [
  age
  employed?
  income
  savings
  pension
  lifetime-wages
  initial-wage
  preferred-firm
  actual-consumption
  visited-firms
  employer
  contract-end
  young?
]

firms-own [
  workers
  production-target
  production-capacity
  production
  inventories
  price
  average-cost
  wage-offer
  debt
  cash
  profits
  equity
  productivity
  missed-payments
  payment-record
  credit-rating
  actual-loan
  firm-interest-rate
  leverage
  sales
  revenue
  vacancies
  size-factor ;规模因子
  firm-kappa;
  liquidating?
  will-reorganize?
]

banks-own [
  total-loans
  bad-debt
  previous-bad-debt
  profit
  loans-portfolio
  total-deposits
]

governments-own [
  fiscal-balance
  tax-income
  pension-expenditure
  pension-balance
  recapitalization-tax
]

to setup
  clear-all

  set pension-system "PAYGO"
  set tau-pi profit-tax-rate
  set phi credit-memory-window
  set contract-duration contract-length
  set max-lifespan 360
  set youth-age-limit 40
  if birth-rate-shift = 0 [ set birth-rate-shift 0 ]

  ;; ===== 新增：run-mode 决定跑多少tick =====
  ;; "historical (40 ticks)"           -> 严格按1994-2003真实数据校准，逐季对照真实日本数据（原有行为，默认）
  ;; "long-run theory check (200 ticks)" -> 只用于验证Okun/Phillips/Beveridge等规律是否涌现，
  ;;                                        tick 40之后外生数据（policy-rates等）自动冻结在2003年最后水平，
  ;;                                        不代表2004年以后的真实历史，跑完后python脚本里把前面一段(建议200 tick)当burn-in丢弃
  ifelse run-mode = "long-run theory check (200 ticks)" [
    set max-ticks 200
  ][
    set max-ticks 40
  ]



ifelse member? simulation-period ["1994-2003" "1994-2003 uniform" "1994-2003 India" "1994-2003 China" "1994-2003 Finland"] [
    set household-count 500 * n*
    set firm-count 25 * n*
    set kappa 1.5                      ;; 初始债务/股权比，1994年日本企业杠杆水平
    set retirement-age retirement-ages            ;; 模型age 181 = 现实60岁（age 0对应15岁，每tick+1）
    set buffer-periods 3               ;; 企业初始现金缓冲 = 3期工资账单，1994年适度保守
    set reserve-years 3.5                ;; 养老金初始储备年数，对应1994年日本年金积立度
    set wealth-consumption-cap 0       ;; 0表示不设财富消费上限，允许household自由动用储蓄

    set initial-inventory-ratio 0.3   ;; 初始库存 = 55%的季度产量，反映泡沫后库存积压
    set reorg-prob        reorganization-prob          ;; 破产企业95%概率重组而非永久死亡，反映日本僵尸企业现象
    set consumer-choice   consumer-choices            ;; 每个消费者每期访问3家企业（含preferred firm）
    set job-application   job-applications            ;; 每个求职者每期申请3家企业

    set ini-price         ini-price-level         ;; 初始价格水平，略高于工资以反映1994年实际价格
    set ini-wage          1.00         ;; 基准工资，归一化为1
    set ini-productivity  1.00         ;; 初始单位劳动生产率，归一化为1
    set ini-production    ini-production-level         ;; 初始季度产量（单位：工资单位），对应约15-16名工人
    set ini-savings       ini-wage * 3 ;; 初始储蓄 = 3个季度工资，约0.75年收入
    set price-adjustment price-adjustments

    set mpc-income-baseline mpc-income
    set mpc-wealth-baseline mpc-wealth

    set credit-threshold credit-thre
    set default-tolerance default-tole

    set real-rgdp-growth  [
    0           -0.005347673  0.011494129  -0.003957873  ; 1994 I-IV
    0.010904365  0.009578850  0.011701146   0.002455290  ; 1995 I-IV
    0.008321189  0.012613091  0.001220142   0.011196363  ; 1996 I-IV
    0.002392138 -0.007276474  0.001889741   0.000395391  ; 1997 I-IV
    -0.012328544 -0.004191365  0.001726302   0.008057437  ; 1998 I-IV
    -0.013900295  0.003974216  0.005282880   0.000369111  ; 1999 I-IV
    0.017216576  0.004503395  0.000235412   0.009746889  ; 2000 I-IV
    0.007321953 -0.007428564 -0.010873785  -0.003431871  ; 2001 I-IV
    0.001642769  0.008086376  0.003223503   0.002783040  ; 2002 I-IV
    0.000578037  0.006797748  0.003055732   0.010929121  ; 2003 I-IV
    ]

    set real-unemp [
    0.0287 0.0280 0.0297 0.0293
    0.0303 0.0307 0.0317 0.0333
    0.0337 0.0340 0.0333 0.0337
    0.0333 0.0333 0.0343 0.0350
    0.0367 0.0407 0.0427 0.0440
    0.0460 0.0473 0.0470 0.0463
    0.0483 0.0470 0.0467 0.0473
    0.0477 0.0490 0.0513 0.0537
    0.0527 0.0540 0.0543 0.0533
    0.0533 0.0543 0.0517 0.0503
    ]

    set real-pension-growth [
    0.0696 0.0594 0.0616 0.0405
    0.0302 0.0154 -0.0167 -0.0188 0.0291
    ]

    set real-inflation [
    0.63 -0.19 0.03 0.47   ; 1994 I-IV
    -0.20 -0.30 0.00 -0.03 ; 1995 I-IV
    0.03 -0.03 0.20 0.03   ; 1996 I-IV
    0.30 -0.08 0.33 -0.03  ; 1997 I-IV
    0.23 -0.13 -0.30 -0.17  ; 1998 I-IV
    -0.43 -0.23 -0.07 -0.30; 1999 I-IV
    0.03 -0.19 -0.16 -0.13 ; 2000 I-IV
    -0.03 -0.46 -0.23 -0.36 ; 2001 I-IV
    -0.33 0.03 -0.13 -0.10 ; 2002 I-IV
    -0.07 0.07 -0.13 -0.20 ; 2003 I-IV
    ]

        ;; 单个工人生产率增长率
    set productivity-growth-rates [
      0.0020 0.0020 0.0020 0.0020   ; 1994 (0.8% / 4)
      0.0065 0.0065 0.0065 0.0065   ; 1995 (2.6%)
      0.00675 0.00675 0.00675 0.00675 ; 1996 (2.7%)
      -0.00025 -0.00025 -0.00025 -0.00025 ; 1997 (-0.1%)
      -0.0015 -0.0015 -0.0015 -0.0015 ; 1998 (-0.6%)
      0.00125 0.00125 0.00125 0.00125 ; 1999 (0.5%)
      0.0075 0.0075 0.0075 0.0075   ; 2000 (3.0%)
      0.00225 0.00225 0.00225 0.00225 ; 2001 (0.9%)
      0.00325 0.00325 0.00325 0.00325 ; 2002 (1.3%)
      0.0045 0.0045 0.0045 0.0045   ; 2003 (1.8%)
    ]

    set wage-increase-rates [
      ; 1993-1994 (ticks ~0-3, 起始年)
    0.006492351 0.006492351 0.006492351 0.006492351
    ; 1994-1995
    0.00251387 0.00251387 0.00251387 0.00251387
    ; 1995-1996
    0.003690354 0.003690354 0.003690354 0.003690354
    ; 1996-1997
    0.002790934 0.002790934 0.002790934 0.002790934
    ; 1997-1998
    0.00016728 0.00016728 0.00016728 0.00016728
    ; 1998-1999
    0.001253761 0.001253761 0.001253761 0.001253761
    ; 1999-2000
    0.001330672 0.001330672 0.001330672 0.001330672
    ; 2000-2001
    0.00297816 0.00297816 0.00297816 0.00297816
    ; 2001-2002
    -0.002616089 -0.002616089 -0.002616089 -0.002616089
    ; 2002-2003
    -0.000413087 -0.000413087 -0.000413087 -0.000413087
    ]

    set productivity-growth-rates map [ g -> g * productivity-growth-scale ] productivity-growth-rates
    set wage-increase-rates map [ g -> g * wage-growth-scale ] wage-increase-rates

    set policy-rates [
      1.75 1.75 1.75 1.75
      1.75 1.00 0.5 0.5
      0.5 0.5 0.5 0.5
      0.5 0.5 0.5 0.5
      0.5 0.5 0.5 0.5
      0.5 0.5 0.5 0.5
      0.5 0.5 0.5 0.5
      0.5 0.35 0.25 0.1
      0.1 0.1 0.1 0.1
      0.1 0.1 0.1 0.1
    ]

    ;; 新增：真实定期存款利率（預入金額3百万円未満/1年）
    set deposit-rates [
    1.71 1.80 1.95 2.10   ; 1994
    2.02 1.11 0.54 0.46   ; 1995
    0.45 0.47 0.41 0.29   ; 1996
    0.27 0.29 0.30 0.26   ; 1997
    0.27 0.25 0.25 0.19   ; 1998
    0.17 0.15 0.14 0.14   ; 1999
    0.13 0.13 0.14 0.16   ; 2000
    0.14 0.06 0.05 0.04   ; 2001
    0.04 0.035 0.034 0.032 ; 2002
    0.032 0.032 0.031 0.031 ; 2003
   ]

    set lend-rates [
      3.000 3.000 3.000 3.000
      3.000 2.375 1.875 1.625
      1.625 1.625 1.625 1.625
      1.625 1.625 1.625 1.625
      1.625 1.625 1.583 1.500
      1.458 1.375 1.375 1.375
      1.375 1.375 1.458 1.500
      1.500 1.375 1.375 1.375
      1.375 1.375 1.375 1.375
      1.375 1.375 1.375 1.375
    ]

    set deposit-rates map [ r -> max list 0 (r + deposit-rate-shift) ] deposit-rates
    set lend-rates map [ r -> max list 0 (r + lend-rate-shift) ] lend-rates

    set paygo-rates [
      0.165  0.165  0.165  0.165
      0.165  0.165  0.165  0.165
      0.1735 0.1735 0.1735 0.1735
      0.1735 0.1735 0.1735 0.1735
      0.1735 0.1735 0.1735 0.1735
      0.1735 0.1735 0.1735 0.1735
      0.1735 0.1735 0.1735 0.1735
      0.1735 0.1735 0.1735 0.1735
      0.1735 0.1735 0.1735 0.1735
      0.1358 0.1358 0.1358 0.1358]
    set pension-annual-returns [
      0.0534 0.0524 0.0499 0.0466 0.0415
      0.0362 0.0322 0.0199 0.0021 0.0491]

;; ===== 初始人口年龄结构（15+岁），按 simulation-period chooser 自动选择 =====
;; 15个bin对应现实15-19...85-89岁5岁组，最后3个bin([300 320][320 340][340 360])
;; 是90+人口按90-94/95-99/100+ 拆分
set age-distributions
  (ifelse-value

    simulation-period = "1994-2003 uniform" [
      ;; ---------- Uniform: 每岁人数密度均匀 ----------
      ;; 设计：18 个 20 岁宽区间，每岁密度约 1.4 人
      ;; - 14 个区间各 28 人 + 4 个高龄区间各 27 人
      ;; - 总人数 = 14×28 + 4×27 = 500（与 baseline 500 完全一致）
      ;; - 退休段（≥180，对应现实 60+）共 220 人，dep ratio ≈ 0.79
      ;; 这是真正"形状均匀"的人口分布，与 baseline 的金字塔形成强对比
      [
        [0 20 28]      [20 40 28]     [40 60 28]
        [60 80 28]     [80 100 28]    [100 120 28]
        [120 140 28]   [140 160 28]   [160 180 28]
        [180 200 28]   [200 220 28]   [220 240 28]
        [240 260 28]   [260 280 28]   [280 300 27]
        [300 320 27]   [320 340 27]   [340 360 27]
      ]
    ]

    simulation-period = "1994-2003 India" [
      ;; 印度 1994（年轻扩张型人口结构，来自populationpyramid.net / UN WPP，15+人口500模型缩放；90+全部为0）
      [
        [0 20 81 ]     [20 40 72 ]     [40 60 64 ]
        [60 80 57 ]    [80 100 50 ]    [100 120 42 ]
        [120 140 32 ]  [140 160 26 ]   [160 180 23 ]
        [180 200 19 ]  [200 220 14 ]   [220 240 10 ]
        [240 260 6 ]   [260 280 3 ]    [280 300 1 ]
        [300 320 0 ]   [320 340 0 ]    [340 360 0 ]
      ]
    ]

    simulation-period = "1994-2003 China" [
      ;; 中国 1994（NBS五岁组普查数据，5-14岁用相邻五岁组线性插值再按已知合计校正；15+按500户模型缩放）
      [
        [0 20 57 ]     [20 40 73 ]     [40 60 72 ]
        [60 80 54 ]    [80 100 51 ]    [100 120 48 ]
        [120 140 33 ]  [140 160 26 ]   [160 180 25 ]
        [180 200 21 ]  [200 220 16 ]   [220 240 12 ]
        [240 260 7 ]   [260 280 4 ]    [280 300 1 ]
        [300 320 0 ]   [320 340 0 ]    [340 360 0 ]
      ]
    ]

    simulation-period = "1994-2003 Finland" [
      ;; 芬兰 1994（UN WPP indicator 47单岁人口，5-14岁为原始单岁数据无需插值；90+合并计入90-94档；15+按500户模型缩放）
      [
        [0 20 40 ]     [20 40 37 ]     [40 60 44 ]
        [60 80 46 ]    [80 100 48 ]    [100 120 50 ]
        [120 140 51 ]  [140 160 35 ]   [160 180 32 ]
        [180 200 30 ]  [200 220 28 ]   [220 240 23 ]
        [240 260 16 ]  [260 280 12 ]   [280 300 6 ]
        [300 320 2 ]   [320 340 0 ]    [340 360 0 ]
      ]
    ]

    [
      ;; ---------- 默认 / "1994-2003": Baseline 1994 真实日本人口结构 ----------
      [
        [0 20 42 ]     [20 40 48 ]     [40 60 41 ]
        [60 80 38 ]    [80 100 38 ]    [100 120 45 ]
        [120 140 48 ]  [140 160 43 ]   [160 180 38 ]
        [180 200 35 ]  [200 220 30 ]   [220 240 21 ]
        [240 260 15 ]  [260 280 11 ]   [280 300 5 ]
        [300 320 1 ]   [320 340 1 ]    [340 360 0 ]
      ]
    ])

    set age-distributions map [dist ->
      (list (item 0 dist) (item 1 dist) (round ((item 2 dist) * n*)))
    ] age-distributions

    ;; ===== 出生数据（新增劳动力，对应真实年龄14→5岁），按 simulation-period chooser 自动选择 =====
    ;; 顺序说明：列表第1项 = 现实14岁（1年后满15岁进入模型），最后1项 = 现实5岁（10年后进入模型）
    let base-births
      (ifelse-value
        simulation-period = "1994-2003 India"     [ [18 18 18 19 19 19 20 20 21 21] ]
        simulation-period = "1994-2003 China"     [ [14 14 14 14 14 13 12 12 12 12] ]
        simulation-period = "1994-2003 Finland"   [ [8 8 8 8 8 8 8 7 8 8] ]
        [ [8 7 7 7 7 7 7 6 6 6] ]) ;; 默认 / "1994-2003" / "1994-2003 uniform"：日本 1994

    set birth-rates-list map [ b -> round ((b + birth-rate-shift) * n*) ] base-births

    ;; ===== 死亡率（per-tick death prob），按 simulation-period chooser 自动选择，对应各国自己的1990-1999 mx（UN WPP indicator 79 / JMD Mx）=====
    let base-death-prob
      (ifelse-value
        simulation-period = "1994-2003 India" [
          [
            [0    20   4.8375E-04]  [20   40   6.1625E-04]  [40   60   6.8025E-04]
            [60   80   7.5925E-04]  [80   100  9.1275E-04]  [100  120  1.1880E-03]
            [120  140  1.7665E-03]  [140  160  2.7040E-03]  [160  180  4.1405E-03]
            [180  200  6.6008E-03]  [200  220  9.9810E-03]  [220  240  1.4798E-02]
            [240  260  2.2013E-02]  [260  280  3.2160E-02]  [280  300  4.6214E-02]
            [300  320  6.4341E-02]  [320  340  8.6938E-02]  [340  360  1.1466E-01]
          ]
        ]
        simulation-period = "1994-2003 China" [
          [
            [0    20   2.0625E-04]  [20   40   2.8575E-04]  [40   60   3.4900E-04]
            [60   80   4.0650E-04]  [80   100  4.9325E-04]  [100  120  7.1800E-04]
            [120  140  1.0020E-03]  [140  160  1.6245E-03]  [160  180  2.3573E-03]
            [180  200  4.2228E-03]  [200  220  6.6850E-03]  [220  240  1.0594E-02]
            [240  260  1.6772E-02]  [260  280  2.8323E-02]  [280  300  4.5131E-02]
            [300  320  7.1950E-02]  [320  340  1.1040E-01]  [340  360  1.4911E-01]
          ]
        ]
        simulation-period = "1994-2003 Finland" [
          ;; ⚠️ 已是芬兰真实mx数据（UN WPP indicator 79，1990-1999均值），与人口结构占位数据无关，可直接使用
          [
            [0    20   1.3600E-04]  [20   40   1.9900E-04]  [40   60   2.1650E-04]
            [60   80   2.7850E-04]  [80   100  4.1725E-04]  [100  120  6.2800E-04]
            [120  140  9.2050E-04]  [140  160  1.3175E-03]  [160  180  1.9243E-03]
            [180  200  3.0540E-03]  [200  220  4.8708E-03]  [220  240  7.9358E-03]
            [240  260  1.3237E-02]  [260  280  2.2557E-02]  [280  300  3.8377E-02]
            [300  320  6.1149E-02]  [320  340  9.2690E-02]  [340  360  1.3118E-01]
          ]
        ]
        [ ;; 默认 / "1994-2003" / "1994-2003 uniform"：日本 1990-1999 mx（JMD All Japan, Mx_5x10）
          [
            [0    20   9.7514E-05]  [20   40   1.2627E-04]  [40   60   1.3078E-04]
            [60   80   1.5954E-04]  [80   100  2.2483E-04]  [100  120  3.5694E-04]
            [120  140  5.8276E-04]  [140  160  9.1400E-04]  [160  180  1.4165E-03]
            [180  200  2.2473E-03]  [200  220  3.4430E-03]  [220  240  5.4644E-03]
            [240  260  9.5878E-03]  [260  280  1.7547E-02]  [280  300  3.0964E-02]
            [300  320  5.2730E-02]  [320  340  8.3501E-02]  [340  360  1.2674E-01]
          ]
        ])

let factor death-prob-shift
set death-prob map [ row ->
  (list
    (item 0 row)
    (item 1 row)
    (min list 1 (max list 0 ((item 2 row) * factor))))
] base-death-prob



 ]
  [ ;; 2009-2018
    set household-count 527 * n*
    set firm-count 25 * n*
    set kappa 0.8
    set retirement-age 201
    set buffer-periods 6
    set reserve-years 3.2
    set wealth-consumption-cap 0

    set initial-inventory-ratio 0.15
    set reorg-prob        0.95
    set consumer-choice   4
    set job-application   4

    set ini-price         1.15
    set ini-wage          1.02
    set ini-productivity  1.13
    set ini-production    16
    set ini-savings       ini-wage * 3

    set mpc-income-baseline 0.85
    set mpc-wealth-baseline 0.05

    set credit-threshold 0.4
    set default-tolerance 0.3
    set price-adjustment 0.01

    set real-rgdp-growth [
    0            0.019589567 -0.000451180  0.012166397  ; 2009 I-IV
    0.010726515  0.012022291  0.018103149 -0.008349738  ; 2010 I-IV
   -0.010311326 -0.008615968  0.024195352 -0.001594150  ; 2011 I-IV
    0.014489995 -0.009401067 -0.003919737 -0.000862289  ; 2012 I-IV
    0.014047956  0.009090528  0.009438493 -0.001289352  ; 2013 I-IV
    0.008286278 -0.017946022  0.000679255  0.004576922  ; 2014 I-IV
    0.015601968  0.001512786  0.000859375 -0.001731566  ; 2015 I-IV
    0.007742811 -0.001714231  0.002032295  0.001315288  ; 2016 I-IV
    0.007871782  0.003955777  0.008667908  0.000516537  ; 2017 I-IV
    0.000787754  0.003945220 -0.004973548 -0.002572280  ; 2018 I-IV
    ]

    set real-unemp [
   0.0457 0.0510 0.0543 0.0520   ; Year 1 I-IV
   0.0503 0.0513 0.0507 0.0500   ; Year 2 I-IV
   0.0473 0.0467 0.0447 0.0447   ; Year 3 I-IV
   0.0450 0.0440 0.0423 0.0417   ; Year 4 I-IV
   0.0420 0.0403 0.0393 0.0387   ; Year 5 I-IV
   0.0367 0.0363 0.0357 0.0347   ; Year 6 I-IV
   0.0350 0.0337 0.0337 0.0327   ; Year 7 I-IV
   0.0323 0.0317 0.0303 0.0300   ; Year 8 I-IV
   0.0290 0.0287 0.0280 0.0270   ; Year 9 I-IV
   0.0247 0.0237 0.0243 0.0247   ; Year 10 I-IV
   ]

    set real-pension-growth [
   -0.0547 -0.0233 0.0573 0.0486
   0.1056 -0.0200 0.0785 0.0724 0.0157
   ]

    set real-inflation [
    -0.91 -0.43 -0.30 -0.40   ; 2009 I-IV
    0.20 -0.18 -0.35 0.18     ; 2010 I-IV
    -0.21 0.00 0.11 -0.21     ; 2011 I-IV
    0.46 -0.21 -0.46 0.00    ; 2012 I-IV
    0.11 0.11 0.67 0.49      ; 2013 I-IV
    0.21 0.24 0.41 -0.27     ; 2014 I-IV 2014q2 2.19换成了0.24
    0.03 0.37 0.00 -0.24     ; 2015 I-IV
    -0.10 0.03 -0.14 0.44     ; 2016 I-IV
    -0.07 0.20 0.07 0.41     ; 2017 I-IV
    0.61 -0.40 0.50 0.13     ; 2018 I-IV
    ]


   set productivity-growth-rates [
     -0.01075 -0.01075 -0.01075 -0.01075   ; 2009 (-4.3%)
     0.011    0.011    0.011    0.011      ; 2010 (4.4%)
     0.00025  0.00025  0.00025  0.00025    ; 2011 (0.1%)
     0.004    0.004    0.004    0.004      ; 2012 (1.6%)
     0.00325  0.00325  0.00325  0.00325    ; 2013 (1.3%)
     -0.001   -0.001   -0.001   -0.001     ; 2014 (-0.4%)
     0.00275  0.00275  0.00275  0.00275    ; 2015 (1.1%)
     -0.00075 -0.00075 -0.00075 -0.00075   ; 2016 (-0.3%)
     0.0015   0.0015   0.0015   0.0015     ; 2017 (0.6%)
     -0.00375 -0.00375 -0.00375 -0.00375   ; 2018 (-1.5%)
   ]

   set wage-increase-rates [
      0.00413 0.00413 0.00413 0.00413
      0.00413 0.00413 0.00413 0.00413
      0.00422 0.00422 0.00422 0.00422
      0.00424 0.00424 0.00424 0.00424
      0.00422 0.00422 0.00422 0.00422
      0.00513 0.00513 0.00513 0.00513
      0.00545 0.00545 0.00545 0.00545
      0.00496 0.00496 0.00496 0.00496
      0.00492 0.00492 0.00492 0.00492
      0.00513 0.00513 0.00513 0.00513
    ]

    set productivity-growth-rates map [ g -> g * productivity-growth-scale ] productivity-growth-rates
    set wage-increase-rates map [ g -> g * wage-growth-scale ] wage-increase-rates

    set policy-rates n-values 40 [0.3] ;10年没有改变

    set deposit-rates [
    0.244 0.223 0.172 0.125   ; 2009
    0.088 0.068 0.065 0.037   ; 2010
    0.035 0.034 0.031 0.027   ; 2011
    0.027 0.026 0.026 0.026   ; 2012
    0.026 0.026 0.026 0.026   ; 2013
    0.026 0.026 0.026 0.026   ; 2014
    0.026 0.026 0.026 0.026   ; 2015
    0.026 0.021 0.015 0.015   ; 2016
    0.015 0.014 0.013 0.011   ; 2017
    0.011 0.011 0.011 0.011   ; 2018
    ]

    set lend-rates n-values 40 [1.475]  ;10年没有改变

    set deposit-rates map [ r -> max list 0 (r + deposit-rate-shift) ] deposit-rates
    set lend-rates map [ r -> max list 0 (r + lend-rate-shift) ] lend-rates

    set paygo-rates [
      0.15704 0.15704 0.15704 0.15704
      0.16058 0.16058 0.16058 0.16058
      0.16412 0.16412 0.16412 0.16412
      0.16766 0.16766 0.16766 0.16766
      0.17120 0.17120 0.17120 0.17120
      0.17474 0.17474 0.17474 0.17474
      0.17828 0.17828 0.17828 0.17828
      0.18182 0.18182 0.18182 0.18182
      0.18300 0.18300 0.18300 0.18300
      0.18300 0.18300 0.18300 0.18300
    ]

    set pension-annual-returns [
     0.0754 -0.0026 0.0217 0.0957 0.0822
     0.1161 -0.0363 0.0547 0.0651 0.0143]

    set age-distributions [
     [0 20 29]     [20 40 33]    [40 60 36]
     [60 80 42]    [80 100 46]   [100 120 41]
     [120 140 37]  [140 160 37]  [160 180 44]
     [180 200 44]  [200 220 40]  [220 240 33]
     [240 260 28]  [260 280 20]  [280 300 11]
     [300 360 6]
    ]

    set age-distributions map [dist ->
      (list (item 0 dist) (item 1 dist) (round ((item 2 dist) * n*)))
    ] age-distributions


    let base-births [5 5 5 6 6 6 6 6 6 6]
    set birth-rates-list map [ b -> round ((b + birth-rate-shift) * n*) ] base-births



    let base-death-prob [
      [0   20   0.00005425]   [20  40   0.00009626]   [40  60   0.00010677]
      [60  80   0.00012902]   [80 100   0.00017330]   [100 120  0.00025985]
      [120 140  0.00040775]   [140 160  0.00064988]   [160 180  0.00099950]
      [180 200  0.00156391]   [200 220  0.00239031]   [220 240  0.00372830]
      [240 260  0.00630080]   [260 280  0.01160314]   [280 300  0.02145756]
      [300 320  0.03930635]   [320 340  0.07016198]   [340 360  0.11969067]
    ]

let factor death-prob-shift
set death-prob map [ row ->
  (list
    (item 0 row)
    (item 1 row)
    (min list 1 (max list 0 ((item 2 row) * factor))))
] base-death-prob

]

  set bankruptcies-this-tick 0
  set pension-balance-history array:from-list n-values 4 [0]





  set tau-w (item 0 paygo-rates) * paygo-rate-scale
  set savings-return-rate (item 0 deposit-rates) / 4 / 100



create-firms firm-count [
  set liquidating? false
  set will-reorganize? false

  set workers []


  set production ini-production + random-float 1          ; 小随机，防止完全相同
  set production-target production ;+ random-float 1      ; 初始 target 略高于 production
  set production-capacity production

  set sales 0

  set inventories production * (initial-inventory-ratio + random-float 0.05)  ;

  set price ini-price + random-float 0.01                   ; 小价格差异
  set profits 0

  set wage-offer ini-wage

  ;; 估一个“初始员工数”用来算工资账单：≈ 生产 / 单人生产率
  let initial-workers max list 1 round (production / ini-productivity)

  set cash buffer-periods * wage-offer * initial-workers


  set firm-kappa kappa * (0.8 + random-float 0.4)
  set equity cash / (firm-kappa + 1)
  set debt cash - equity

  set productivity ini-productivity + random-float 0.05
  set missed-payments 0
  set payment-record n-values phi [0]
  set actual-loan 0
  set firm-interest-rate (item 0 policy-rates) / 100 / 4
  set leverage debt / equity
  set vacancies 0

  setxy random-xcor random-ycor
  set shape "factory"
  set color blue
]

  set total-demand 0;sum[sales] of firms
  set tracked-firm one-of firms

  create-households household-count [
    let assigned false
    let i 0
    while [not assigned and i < length age-distributions] [
      if item 2 (item i age-distributions) > 0 [
        let age-range item i age-distributions
        set age random (item 1 age-range - item 0 age-range) + item 0 age-range
        let current-count item 2 (item i age-distributions)
        set age-distributions replace-item i age-distributions (replace-item 2 (item i age-distributions) (current-count - 1))
        set assigned true
      ]
      set i i + 1
    ]
    set employed? false
    set actual-consumption 0
    set income 0 ;ini-wage * 0.9
    set savings ini-savings + random-float 1 ;;
    set lifetime-wages []
    if age > 0 [
  let quarters-worked min list age retirement-age
  set lifetime-wages n-values quarters-worked [ini-wage * 0.9]
 ]

    set employer nobody
    set contract-end 0
    set young? age <= youth-age-limit
    setxy random-xcor random-ycor
    set shape "person"
    set color ifelse-value (age >= retirement-age) [red] [ifelse-value age <= 80 [yellow] [green]]
  ]

  create-banks 1 [
    set total-loans 0
    set bad-debt 0
    set previous-bad-debt 0
    set profit 0
    set loans-portfolio []
    set total-deposits 0
    setxy 0 0
    set shape "building institution"
    set color violet
  ]

  create-governments 1 [
    set tax-income 0
    set pension-expenditure 0
    set fiscal-balance 0
    set pension-balance 0
    setxy 0 10
    set shape "house"
    set color gray
  ]




set market-price mean [price] of firms ;初始设定，后面会更新

  ;; --- initialize demand consistently (units) ---
  ;;let avg-price-init mean [price] of firms
  ;;if avg-price-init <= 0 [ set avg-price-init ini-price ]
  ;;let total-budget-init sum [ (mpc-income * income) + (mpc-wealth * savings) ] of households
  ;;set total-demand total-budget-init / avg-price-init


set previous-market-price market-price
set base-price market-price


;; CPI 以100为基准
set cpi 100
set previous-cpi 100
set inflation (cpi - previous-cpi) / previous-cpi

;; ===== GDP =====
;; 初始化名义/真实gdp
set nominal-gdp sum [production * price] of firms
set real-gdp nominal-gdp / (cpi / 100)


;; ===================================================
;; 直接设置初始失业率（1994 Q1 数据）
;; ===================================================

;; 1. 直接定义初始失业率
ifelse member? simulation-period ["1994-2003" "1994-2003 uniform" "1994-2003 India" "1994-2003 China" "1994-2003 Finland"] [
  set initial-young-unemp 5.33
  set initial-old-unemp   2.46
][
  set initial-young-unemp 8.73
  set initial-old-unemp   4.16
]

;; 2. 转换为就业率
let initial-young-emp-rate 1 - (initial-young-unemp / 100)
let initial-old-emp-rate 1 - (initial-old-unemp / 100)

;; 3. 分别处理年轻人和中年人
let young-workers households with [age < retirement-age and young?]
let old-workers households with [age < retirement-age and not young?]

  ;; 同时强制退休者状态
ask households with [age >= retirement-age] [
  set employed? false
  set employer nobody
]

;; 4. 计算需要就业的人数
let young-to-employ round (count young-workers * initial-young-emp-rate)
let old-to-employ round (count old-workers * initial-old-emp-rate)

;; 5. 随机选择就业者
let young-employed n-of young-to-employ young-workers
let old-employed n-of old-to-employ old-workers
let all-employed (turtle-set young-employed old-employed)

;; 6. 为就业者分配雇主
let firms-to-hire firms with [true]
foreach sort all-employed [ worker ->
  ask worker [
    set employed? true
    let chosen-firm min-one-of firms-to-hire [length workers]
    set employer chosen-firm
    set contract-end random contract-duration  ;; 改：直接用随机值，
    set initial-wage [wage-offer] of chosen-firm
    ask chosen-firm [
      set workers lput worker workers
    ]
  ]
]


  ask firms [
    foreach workers [ w ->
      ask w [
        set initial-wage [wage-offer] of myself
      ]
    ]
  ]

 ;; ===== 直接初始化 tick 0 的失业率 =====
  let labour-force households with [age < retirement-age]
  let unemployed-labour-force labour-force with [not employed?]

  let young-labour-force households with [age <= youth-age-limit and age < retirement-age]
  let old-labour-force households with [age > youth-age-limit and age < retirement-age]

  let unemployed-young young-labour-force with [not employed?]
  let unemployed-old old-labour-force with [not employed?]

  set young-unemployment ifelse-value (count young-labour-force > 0)
    [count unemployed-young / count young-labour-force]
    [0]

  set old-unemployment ifelse-value (count old-labour-force > 0)
    [count unemployed-old / count old-labour-force]
    [0]

  set total-unemployment ifelse-value (count labour-force > 0)
    [count unemployed-labour-force / count labour-force]
    [0]

  set total-workers count labour-force
  set total-vacancies sum [vacancies] of firms
  set vacancy-rate ifelse-value (total-workers > 0)
    [total-vacancies / total-workers]
    [0]

;; ===== 先初始化所有退休者（按当前retirement-age）的养老金 =====
ask households with [age >= retirement-age] [
  ifelse length lifetime-wages > 0 [
    set pension mean lifetime-wages * pension-replace-scale
  ][ set pension 0 ]
]

;; ===== 额外：为 baseline 边界（181）以上但当前不是退休者的人 =====
;; 临时计算他们如果退休应得的 pension，仅用于初始化 pension-balance
;; 不改变他们的实际 pension 值（他们还是劳动力）
let baseline-quarterly-benefits 0
ask households with [age >= retirement-age] [
  let this-pension ifelse-value (length lifetime-wages > 0)
    [ mean lifetime-wages * pension-replace-scale ]
    [ 0 ]
  set baseline-quarterly-benefits baseline-quarterly-benefits + this-pension
]

let reserve-quarters reserve-years * 4

;; ===== 初始化 pension-balance =====
;; 锚定 1994 年日本真实养老金积立金水平（历史给定值）。
;; 反事实逻辑：假设人口结构不同，但养老金基金规模继承真实历史。
;; 公式：reserve-quarters × baseline 设计退休人数 × 替代率 × ini-wage × 0.9
;;   - baseline 设计退休人数 = 119 × n*（1994 真实人口结构）
;;   - 0.9 来自 setup 中 lifetime-wages 的初值 (ini-wage * 0.9)
;; baseline 和 uniform 都用这个数，确保从相同的"历史起点"出发。
let baseline-retirees-count 119 * n*
let baseline-quarterly-benefits-historical baseline-retirees-count * pension-replace-scale * ini-wage * 0.9
let historical-pension-balance reserve-quarters * baseline-quarterly-benefits-historical

ask one-of governments [
  set pension-expenditure sum [pension] of households with [age >= retirement-age]
  set pension-balance historical-pension-balance
]

  ;; 如果你后面会用 pension-balance-history，也顺手初始化
  set pension-balance-history array:from-list n-values 4 [[pension-balance] of one-of governments]


  ;---------------------------------
  ;; 初始化就业者收入
ask households with [employed?] [
  if is-agent? employer [
    let current-wage [wage-offer] of employer
    set income current-wage * (1 - tau-w / 2) + savings * savings-return-rate
  ]
]

;; 初始化退休者收入
ask households with [age >= retirement-age] [
  set income pension + savings * savings-return-rate
]
  ;----------------------------------



reset-ticks
  update-statistics

set previous-real-gdp real-gdp
set previous-unemployment total-unemployment
set initial-total-loans sum [debt] of firms
set previous-year-pension-balance [pension-balance] of one-of governments
set annual-pension-growth 0

end

to go

  ;; reset death counters at the start of each tick
  set deaths-15-19  0
  set deaths-20-24  0
  set deaths-25-29  0
  set deaths-30-34  0
  set deaths-35-39  0
  set deaths-40-44  0
  set deaths-45-49  0
  set deaths-50-54  0
  set deaths-55-59  0
  set deaths-60-64  0
  set deaths-65-69  0
  set deaths-70-74  0
  set deaths-75-79  0
  set deaths-80-84  0
  set deaths-85-89  0
  set deaths-90-94  0
  set deaths-95-99  0
  set deaths-100plus 0



  if ticks >= max-ticks [ stop ]

  if ticks < length productivity-growth-rates [
    let growth item ticks productivity-growth-rates
    ask firms [
      set productivity productivity * (1 + growth)
      set production-capacity productivity * length workers
    ]
  ]

  if ticks < length deposit-rates [
    let annual-rate item ticks deposit-rates
    set savings-return-rate annual-rate / 4 / 100
  ]

  if ticks < length paygo-rates [
  set tau-w (item ticks paygo-rates) * paygo-rate-scale
]

  ;if ticks = 400 [
  ;  set retirement-age delayed-age
  ;]

  ask firms [firm-decisions]
  labor-market
  ask firms [update-credit-rating]
  ask firms [apply-for-loan]
  check-financial-firing
  ask firms [update-production-capacity]
  ask firms [produce]
  ask households [
    update-income
  ]
  calculate-demand
  goods-market
  ask firms [firm-financials]
  ask firms [update-credit-rating]
  bank-financial-update
  firm-exit-and-entry
  ask households [check-death]
  add-new-births ;新增：每四个tick新出生固定人数
  ask households [age-and-retire]
  update-pensions

  ;; ===== 更新价格与 CPI =====
  set previous-market-price market-price
  ;market-price 已在 goods-market 中计算（成交加权）

  ;; 直接用当前均价计算 CPI（无平滑）
  set previous-cpi cpi
  set cpi (market-price / base-price) * 100   ;; base-price 仍固定为初始值
  set inflation (cpi - previous-cpi) / previous-cpi

  ;; ===== 更新GDP =====

  set nominal-gdp sum [production * price] of firms  ;;此时liquidating 的公司production 是0 ，其实不加with [not liquidating?] 也没关系。
  ;; 实际GDP = 名义GDP / (CPI/100)
  if cpi != 0 [
    set real-gdp nominal-gdp / (cpi / 100)
  ]



  update-statistics
  ;plot-age-distribution-histogram
  ;plot-consumption-by-age-histogram


  tick
end

to firm-decisions
  if liquidating? [ stop ]






  ifelse inventories = 0 and price >= previous-market-price [
    set production-target production-target * (1 + random-float production-adjustment)
    ;; 新增：封顶只在long-run模式下生效，historical(40 tick)模式完全保持原始未修改的行为，
    ;; 不影响1994-2003历史校准/fit_stats那部分已经跑出来的结果
    if run-mode = "long-run theory check (200 ticks)" [
      if production-target > production-capacity * target-cap-multiplier [
        set production-target production-capacity * target-cap-multiplier
      ]
    ]
  ][
    if inventories > 0 and price < previous-market-price [
      set production-target production-target * (1 - random-float production-adjustment)
    ]
  ]


  set production-capacity productivity * length workers
  let desired-workers ceiling (production-target / productivity)
  if desired-workers < 0 [set desired-workers 0]
  let expired-workers []
  let retiring-workers []
  let active-workers workers
  foreach active-workers [ w ->
    if [contract-end] of w <= ticks [
      set expired-workers lput w expired-workers
    ]
    if [age] of w >= retirement-age [
      set retiring-workers lput w retiring-workers
    ]
  ]
  foreach retiring-workers [ w ->
    ask w [
      set employed? false
      set employer nobody
      set contract-end 0
    ]
    set workers remove w workers
  ]

  let current-workers length workers
  let renewed-workers 0
  if not empty? expired-workers [
    foreach expired-workers [ w ->
      if current-workers + renewed-workers < desired-workers [
        ask w [
          set contract-end ticks + random contract-duration
          set initial-wage [wage-offer] of myself
        ]
        set renewed-workers renewed-workers + 1
      ]
      if current-workers + renewed-workers >= desired-workers [
        ask w [
          set employed? false
          set employer nobody
          set contract-end 0
        ]
        set workers remove w workers
      ]
    ]
  ]
  set current-workers length workers + renewed-workers
  set vacancies 0
  if current-workers < desired-workers [
    set vacancies desired-workers - current-workers
  ]

  if ticks < length wage-increase-rates [
  let g item ticks wage-increase-rates   ;; g 是本季度增长率，例如 0.003 代表 +0.3%
  set wage-offer wage-offer * (1 + g)
  ]

  foreach workers [ w ->
    ask w [
      set initial-wage [wage-offer] of myself
    ]
  ]
  set production production-target
  if production > production-capacity [
    set production production-capacity
  ]
  let avg-cost 0
  if production > 0 and length workers > 0 [
    let total-wage wage-offer * length workers
    let employer-pension-contribution total-wage * (tau-w / 2)
    set avg-cost (total-wage + employer-pension-contribution + firm-interest-rate * debt) / production ;算上养老金的平均成本
  ]


  let inventory-ratio ifelse-value (production-target > 0)
    [ inventories / production-target ]
    [ 0 ]

  ifelse inventories = 0  and price < previous-market-price [
    set price price * (1 + random-float price-adjustment)
  ][
    if inventories > 0 and price >= previous-market-price [
      set price price * (1 - random-float price-adjustment )
    ]
  ]
  set price max (list price avg-cost)

end

to labor-market
  set total-vacancies sum [vacancies] of firms
  let unemployed-workers households with [age < retirement-age and not employed?]
  ask unemployed-workers [
    let M job-application
    let potential-firms n-of (min list M count firms) firms
    if is-agent? employer and member? employer firms and [vacancies > 0] of employer [
      set potential-firms (turtle-set potential-firms employer)
    ]
    let best-firm nobody
    let best-wage 0
    foreach sort-on [(- wage-offer)] (potential-firms with [vacancies > 0]) [ f ->
      if [wage-offer] of f > best-wage [
        set best-wage [wage-offer] of f
        set best-firm f
      ]
    ]
    if is-agent? best-firm [
      set employed? true
      set employer best-firm
      set contract-end ticks + contract-duration
      set initial-wage [wage-offer] of best-firm
      ask best-firm [
        set workers lput myself workers
        set vacancies vacancies - 1
      ]
    ]
  ]
  ask firms [
    foreach workers [ w ->
      ask w [
        set initial-wage [wage-offer] of myself
      ]
    ]
  ]
end

to update-production-capacity
  if liquidating? [
    set production-capacity 0
    stop
  ]

  set production-capacity productivity * length workers
end

to produce
  if liquidating? [
    set production 0
    stop
  ]
  set production min (list production-target production-capacity)
  set inventories inventories + production
end


to apply-for-loan
  if liquidating? [ set actual-loan 0 stop ]

  set actual-loan 0
  let wage-bill wage-offer * length workers
  let employer-pension-contribution wage-bill * (tau-w / 2)
  let required-labor-payment wage-bill + employer-pension-contribution ;申请贷款的时候要算上给员工缴纳的养老金

  if cash < required-labor-payment [
    let loan-request max (list (required-labor-payment - cash) 0)
    if credit-rating > credit-threshold [
      set actual-loan loan-request
      ask one-of banks [
        set total-loans total-loans + loan-request
        set loans-portfolio lput (list myself loan-request) loans-portfolio
      ]
    ]
  ]
end

to check-financial-firing
  ask firms [
    if liquidating? [ stop ]

    let wage-bill wage-offer * length workers
    let employer-pension-contribution wage-bill * (tau-w / 2)
    let labor-cost wage-bill + employer-pension-contribution

    let can-pay-labor-cost? (cash + actual-loan >= labor-cost)

    if not can-pay-labor-cost? [
      let desired-workers ceiling (production-target / productivity)
      let excess-workers length workers - desired-workers
      if excess-workers > 0 [
        let workers-to-fire n-of excess-workers workers
        foreach workers-to-fire [ w ->
          ask w [
            set employed? false
            set employer nobody
            set contract-end 0
          ]
          set workers remove w workers
        ]
        set production-capacity productivity * length workers
      ]
    ]
  ]
end

to age-and-retire
  set age age + 1
  set young? age <= youth-age-limit
  if age >= retirement-age [set color red]
  if age < retirement-age and age <= youth-age-limit [set color yellow]
  if age < retirement-age and age > youth-age-limit [set color green]
  if age >= retirement-age and employed? [
    set employed? false
    set employer nobody
    set contract-end 0
    set color red
  ]
  if employed? and ticks >= contract-end [
  let old-employer employer
  set employed? false
  set employer nobody
  if is-agent? old-employer [
    ask old-employer [
      set workers remove myself workers
    ]
  ]
]
end

to update-income ; 更新收入（利息+养老金）
  let interest-income savings * savings-return-rate
  ifelse employed? [
    if is-agent? employer [
      let current-wage [wage-offer] of employer
      set income current-wage * (1 - tau-w / 2) + interest-income
      set lifetime-wages lput current-wage lifetime-wages
      if length lifetime-wages > (retirement-age) [
        set lifetime-wages but-first lifetime-wages
      ]
    ]
  ][
    ifelse age >= retirement-age [
      ifelse length lifetime-wages > 0 [
        let avg-lifetime-wage mean lifetime-wages
        set pension avg-lifetime-wage * pension-replace-scale
      ][
        set pension 0
      ]
      set income pension + interest-income
    ][

      set income  interest-income


    ]
  ]
end


to calculate-demand
  let avg-price mean [price] of firms

  ;; 分组
  let employed-hh households with [employed?]
  let unemployed-hh households with [not employed? and age < retirement-age]
  let retired-hh households with [age >= retirement-age]

  ;; 各组的income-driven部分
  let emp-income-budget sum [mpc-income-baseline * income] of employed-hh
  let unemp-income-budget sum [mpc-income-baseline * income] of unemployed-hh
  let ret-income-budget sum [mpc-income-baseline * income] of retired-hh

  ;; 各组的wealth-driven部分
  let emp-wealth-budget sum [mpc-wealth-baseline * savings] of employed-hh
  let unemp-wealth-budget sum [mpc-wealth-baseline * savings] of unemployed-hh
  let ret-wealth-budget sum [mpc-wealth-baseline * savings] of retired-hh



  let total-budget emp-income-budget + unemp-income-budget + ret-income-budget
                 + emp-wealth-budget + unemp-wealth-budget + ret-wealth-budget
  set total-demand total-budget / avg-price
end


to goods-market
  ;set market-price mean [price] of firms
  ask firms [
    set sales 0
    set revenue 0
  ]

  let shopping-households households with [income > 0 or savings > 0]
  ask shopping-households [

let wealth-part (ifelse-value (wealth-consumption-cap > 0)
  [ min list (mpc-wealth-baseline * savings) wealth-consumption-cap ]
  [ mpc-wealth-baseline * savings ])

let consumption-budget (mpc-income-baseline * income) + wealth-part

    let visited-firms-list []
    let random-firms n-of (min list (consumer-choice - 1) count firms) firms
    set visited-firms-list sort random-firms
    if is-agent? preferred-firm and member? preferred-firm firms [
      set visited-firms-list lput preferred-firm visited-firms-list
    ]
    let sorted-firms sort-by [[a b] -> [price] of a < [price] of b] visited-firms-list
    let consumed 0
    let max-sales-firm nobody
    let max-sales 0
    foreach sorted-firms [ f ->
      if is-agent? f [
        let firm-price [price] of f
        let firm-inventories [inventories] of f
        if firm-price > 0 and firm-inventories > 0 [
          let units-to-buy min list ((consumption-budget - consumed) / firm-price) firm-inventories
          if units-to-buy > 0 [
            let purchase-cost units-to-buy * firm-price
            set consumed consumed + purchase-cost
            ask f [
              set sales sales + units-to-buy
              set revenue revenue + (units-to-buy * price)
              set inventories inventories - units-to-buy
              if inventories < 0 [set inventories 0]
              if sales > max-sales [
                set max-sales sales
                set max-sales-firm self
              ]
            ]
          ]
        ]
      ]
    ]
    set preferred-firm max-sales-firm
    set actual-consumption consumed
    set savings savings + income - consumed
  ]
  ;; === 新增：成交加权均价 ===
  let total-sales sum [sales] of firms
  let total-revenue sum [revenue] of firms

  ifelse total-sales > 0
  [ set market-price total-revenue / total-sales ]   ;; 成交均价，销量大的企业权重高，反映实际市场成交，成交加权价格更接近真实CPI。
  ;;成交加权价格 < 简单平均价格, 说明：低价企业卖得更多, 符合需求规律（价格弹性）
  [ set market-price mean [price] of firms ]         ;; 没成交时兜底
end

to firm-financials

  if liquidating? [
    ; 只把销售收入加到现金里（goods-market 已经写 revenue）
    set cash cash + revenue
    ; debt 不动、工资不动、利息不动
    stop
  ]

  set cash cash + actual-loan
  set debt debt + actual-loan
  let wage-bill wage-offer * length workers
  let employer-pension-contribution wage-bill * (tau-w  / 2);; 新增：雇主缴费
  let interest-payment debt * firm-interest-rate
  let debt-repayment debt * debt-repayment-rate
  let total-payment interest-payment + debt-repayment
  set cash cash + revenue - wage-bill - employer-pension-contribution
  let cash-before-repayment cash
  set cash cash - total-payment
  let missed-this-period 0
  if cash < 0 [
    set missed-this-period 1
    set debt debt - cash
    set cash 0
  ]
  if missed-this-period = 0 [
    set debt debt - debt-repayment
    if debt < 0 [set debt 0]
  ]
  set payment-record but-first payment-record
  set payment-record lput missed-this-period payment-record
  set missed-payments sum payment-record
  set profits revenue - wage-bill - employer-pension-contribution - interest-payment
  set equity equity + profits


let profit-tax 0
if profits > 0 [
  set profit-tax profits * tau-pi
]


  set cash cash - profit-tax
  if cash >= 0 [
    ask one-of governments [
      set tax-income tax-income + profit-tax
    ]
  ]
  if cash < 0 [
    let paid-tax (profit-tax + cash)
    ask one-of governments [
      set tax-income tax-income + paid-tax
    ]
    set debt debt - cash
    set cash 0
  ]
;; ===== Balance sheet closure =====
  ;; ===== Balance sheet closure（唯一一次equity和leverage计算）=====
  let inventory-value inventories * price
  set equity cash + inventory-value - debt
  set equity max list equity 1e-6  ;; 统一用max list，不用if语句
  set leverage debt / equity
end

to bank-financial-update
  ask banks [
    let interest-income sum [debt * firm-interest-rate] of firms
    let interest-expense sum [savings * savings-return-rate] of households
    let new-bad-debt (bad-debt - previous-bad-debt)
    set profit interest-income - interest-expense - new-bad-debt
    set previous-bad-debt bad-debt
    set total-loans sum [debt] of firms
    set total-deposits sum [savings] of households

    ifelse initial-total-loans > 0
      [ set loan-index total-loans / initial-total-loans ]
      [ set loan-index 0 ]
  ]
end

to update-credit-rating
  ; 1. 计算信用评级（保持不变）
  set credit-rating (Phi - missed-payments) / Phi
  if credit-rating < 0 [set credit-rating 0]
  if credit-rating > 1 [set credit-rating 1]

  ; 2. 获取当期基准利率（超过真实数据长度后，冻结在最后一期的水平，避免越界报错）
  let base-rate (item (min list ticks (length policy-rates - 1)) policy-rates) / 100 / 4

  ; 3. 计算风险溢价（基于信用评级和杠杆率）
  let risk-premium 0

  ; 信用评级越低，溢价越高
  let credit-factor (1 - credit-rating)  ; 0到1，越高越差

  ; 杠杆率越高，溢价越高
  ;let leverage-factor min list (leverage / 3) 1  ;
let cash-leverage ifelse-value (cash > 0)
  [ debt / cash ]
  [ 99 ]  ;; 没有现金时设为极大值
let leverage-factor min list (cash-leverage / 10) 1

  ; 综合风险溢价：0.2% 到 4%
  set risk-premium 0.002 + (credit-factor * 0.015) + (leverage-factor * 0.015) + (random-float 0.008)

  ; 4. 最终利率 = 基准利率 + 风险溢价
  set firm-interest-rate base-rate + risk-premium

  ; 5. 设置上下限
  set firm-interest-rate min list firm-interest-rate 0.07   ;上限7%
end

to firm-exit-and-entry

  ;; =========================================================
  ;; 0) 选出“新触发破产且尚未进入清算”的企业
  ;; =========================================================
  let newly-bankrupt firms with [
    (not liquidating?) and (credit-rating < default-tolerance)
  ]



  set bankruptcies-this-tick count newly-bankrupt  ; 新增：统计本tick新破产数

  ;; =========================================================
  ;; 1) 新破产企业 -> 进入清算（不立刻 die、不搬库存到 globals）
  ;; =========================================================
  if any? newly-bankrupt [
    ask newly-bankrupt [

      ;; 1.1 决定这家企业清算结束后：重组 or 永久死亡
      ifelse random-float 1 < reorg-prob
      [ set will-reorganize? true ]
      [ set will-reorganize? false ]

      ;; 1.2 解雇所有工人（停工资、停合同）
      foreach workers [ w ->
        ask w [
          set employed? false
          set employer nobody
          set contract-end 0
        ]
      ]
      set workers []
      set vacancies 0

      ;; 1.3 进入清算状态：不生产，只卖库存
      set liquidating? true
      set production-target 0
      set production 0
      set production-capacity 0

      ;; 1.4 折价清仓：
      ; 找到正常企业的最低价
  let active-firms firms with [not liquidating? and credit-rating >= default-tolerance]

  ifelse any? active-firms [
    let market-low-price min [price] of active-firms

    set price market-low-price  * 0.95  ; 比市场最低价低5%
  ][

    set price price * 0.5  ; 兜底：如果没有正常企业，打5折
  ]


      ;; 1.5 关掉贷款（避免清算期继续借钱）
      set actual-loan 0
    ]
  ]

  ;; =========================================================
  ;; 2) 清算结束：库存卖空的清算企业 -> 银行结算 -> die 或重组
  ;; =========================================================
  let finished-liquidations firms with [ liquidating? and inventories <= 0 ]

  if any? finished-liquidations [

    ;; 2.1 分成“清算后死亡”和“清算后重组”
    let firms-to-die finished-liquidations with [ not will-reorganize? ]
    let firms-to-reorganize finished-liquidations with [ will-reorganize? ]

    ;; ---------------------------------------------------------
    ;; A) 清算后死亡：先结算银行坏账，再 die
    ;; ---------------------------------------------------------
    if any? firms-to-die [
      ask firms-to-die [
        settle-bank-and-record-baddebt
        die
      ]
    ]

    ;; ---------------------------------------------------------
    ;; B) 清算后重组：先统一征税筹资，再批量重置
    ;; ---------------------------------------------------------
    if any? firms-to-reorganize [
      recapitalize-and-reset (turtle-set firms-to-reorganize)
    ]
  ]

end

to settle-bank-and-record-baddebt  ;; firm context

  ;; 清算结束后：库存已卖空，资产只剩 cash
  let total-assets max list cash 0
  let total-liabilities debt

  let recovery-rate 0
  if total-liabilities > 0 [
    set recovery-rate min list 1 (total-assets / total-liabilities)
  ]

  let recovered debt * recovery-rate
  let bad debt - recovered

  ask one-of banks [
    set bad-debt bad-debt + bad
  ]

  ;; 清算后旧账清零（重组前也需要这步）
  set cash 0
  set debt 0
  set equity 0
end

to recapitalize-and-reset

  [reorg-set]  ;; observer context

  ;; 模板企业：只从“正常经营且不清算”的企业里找
  let active-firms firms with [ (not liquidating?) and (credit-rating >= default-tolerance) ]

  ;; 1) 计算每家重组企业目标现金（用模板现金作参考）
  let target-cash-list []
  ask reorg-set [
    let target 100
    if any? active-firms [ set target [cash] of one-of active-firms ]
    set target-cash-list lput target target-cash-list
  ]
  let total-target sum target-cash-list

  ;; 2) 征财富税筹资
  let collected 0
  if total-target > 0 [
    let total-wealth sum [savings] of households
    if total-wealth > 0 [
      let tax-rate min (list (total-target / total-wealth) wealth-tax-cap)
      ask households [
        let pay savings * tax-rate
        set savings savings - pay
        if savings < 0 [ set savings 0 ]
        set collected collected + pay
      ]
    ]
  ]

  ;; 3) 分配比例（可能没筹够）
  let ratio 0
  if total-target > 0 [ set ratio min list 1 (collected / total-target) ]

  ;; 4) 批量重置企业
  let idx 0
  ask reorg-set [

    ;; 4.1 先把旧债结算掉（非常关键）
    settle-bank-and-record-baddebt

    ;; 4.2 复制模板参数（或兜底）
    if any? active-firms [
      let template one-of active-firms
      set production-target [production-target] of template
      set production [production] of template
      set productivity [productivity] of template
      set wage-offer [wage-offer] of template
      set price [price] of template
      let template-kappa [firm-kappa] of template
      set firm-kappa template-kappa
    ]
    if not any? active-firms
    [
      set production-target 5
      set production 0
      set productivity (1 + random-float 0.05)
      set wage-offer ini-wage
      set price ini-price
    ]

    ;; 4.3 新公司库存 = 0（守恒 + 避免凭空多出来）
    set inventories 0

    ;; 4.4 注资到账
    let target item idx target-cash-list
    let cash-in target * ratio
    set idx idx + 1

    set cash cash-in
    set equity cash / (firm-kappa + 1)
    set debt cash - equity
    set leverage debt / max list equity 1e-6

    ;; 4.5 重置信用与状态
    set credit-rating 1
    set payment-record n-values phi [0]
    set missed-payments 0
    set firm-interest-rate (item (min list ticks (length policy-rates - 1)) policy-rates) / 100 / 4
    set actual-loan 0
    set vacancies 0

    ;; 4.6 退出清算状态
    set liquidating? false
    set will-reorganize? false
  ]

  ;; 5) 政府财政记账（可选：按你自己的口径）
  ask one-of governments [
    set recapitalization-tax recapitalization-tax + collected
    set fiscal-balance fiscal-balance + collected
  ]
end




to check-death
  let bin-index min (list (floor (age / 20)) (length death-prob - 1))
  let prob item 2 (item bin-index death-prob)

  if random-float 1 < prob or age >= max-lifespan [

    ;; ← 新增：记录死亡，按年龄组分桶
    record-death age

    if employed? and is-agent? employer [
      ask employer [
        set workers remove myself workers
        set production-capacity productivity * length workers
      ]
    ]
    ask one-of governments [
      set fiscal-balance fiscal-balance + [savings] of myself
    ]
    die
  ]
end

to record-death [a]
  let idx min (list (floor (a / 20)) 17)   ;; 注意：上限改成 17（共 18 档）

  (ifelse
    idx = 0  [ set deaths-15-19   deaths-15-19   + 1 ]
    idx = 1  [ set deaths-20-24   deaths-20-24   + 1 ]
    idx = 2  [ set deaths-25-29   deaths-25-29   + 1 ]
    idx = 3  [ set deaths-30-34   deaths-30-34   + 1 ]
    idx = 4  [ set deaths-35-39   deaths-35-39   + 1 ]
    idx = 5  [ set deaths-40-44   deaths-40-44   + 1 ]
    idx = 6  [ set deaths-45-49   deaths-45-49   + 1 ]
    idx = 7  [ set deaths-50-54   deaths-50-54   + 1 ]
    idx = 8  [ set deaths-55-59   deaths-55-59   + 1 ]
    idx = 9  [ set deaths-60-64   deaths-60-64   + 1 ]
    idx = 10 [ set deaths-65-69   deaths-65-69   + 1 ]
    idx = 11 [ set deaths-70-74   deaths-70-74   + 1 ]
    idx = 12 [ set deaths-75-79   deaths-75-79   + 1 ]
    idx = 13 [ set deaths-80-84   deaths-80-84   + 1 ]
    idx = 14 [ set deaths-85-89   deaths-85-89   + 1 ]
    idx = 15 [ set deaths-90-94   deaths-90-94   + 1 ]
    idx = 16 [ set deaths-95-99   deaths-95-99   + 1 ]
             [ set deaths-100plus deaths-100plus + 1 ]   ;; idx >= 17
  )
end

to add-new-births
  if ticks mod 4 = 0 [
    let year-index floor (ticks / 4)
    ;; 新增：超过真实历史数据长度(2003年)后，冻结在最后一年(2003)的出生数继续生育，
    ;; 而不是像原来那样直接完全停止出生——原来的写法会导致tick>40后人口只减不增，
    ;; 在max-lifespan=360的设定下最终整个households population会灭绝。
    let clamped-year-index min list year-index (length birth-rates-list - 1)
    let annual-births item clamped-year-index birth-rates-list

    create-households annual-births [
      set age 0
      set young? true
      set employed? false
      set income 0
      set pension 0
      set lifetime-wages []
      set savings ini-savings + random-float 1
      set employer nobody
      set contract-end 0
      set preferred-firm nobody
      set actual-consumption 0
      set initial-wage 0
      set young? true
      setxy random-xcor random-ycor
      set shape "person"
      set color yellow
    ]
  ]
end

to update-pensions ;  更新养老金的计算(收取，发放，投资收益)

  let prev-balance [pension-balance] of one-of governments

  let contributors households with [employed? and age < retirement-age]

  ;; ===== 1. 当期投资收益（按季度复利,只对期初 balance 计息） =====
  ;; 关键修复:把年化收益率转换为季度复利,在收缴费之前对期初 balance 应用,
  ;; 避免"当季新缴费立刻享受全年投资收益"的过度放大。
  let year-index floor (ticks / 4)
  ;; 新增：超过真实历史数据长度后，冻结在最后一年的投资收益率，而不是停止计息(原来会变相变成0%收益)
  let clamped-pension-year-index min list year-index (length pension-annual-returns - 1)
  if clamped-pension-year-index >= 0 [
    let annual-r item clamped-pension-year-index pension-annual-returns
    let quarterly-r (1 + annual-r) ^ 0.25 - 1   ;; 年化 → 季度复利
    ask governments [
      set pension-balance pension-balance * (1 + quarterly-r)
    ]
  ]

  ;; ===== 2. 当期缴费（税前工资 × 费率） =====
  let total-wage-bill sum [[wage-offer] of employer] of contributors
  let employee-contributions total-wage-bill * tau-w / 2  ;; 雇员缴费
  let employer-contributions total-wage-bill * tau-w / 2  ;; 雇主缴费
  let total-contributions employee-contributions + employer-contributions
  set pension-contributions total-contributions

  ask governments [
    set pension-balance pension-balance + total-contributions
    set pension-expenditure 0
  ]

  ;; ===== 3. 记录并支付当期养老金支出 =====
  let retirees households with [age >= retirement-age]
  let total-benefits sum [pension] of retirees
  set pension-benefits total-benefits

  ask governments [
    set pension-expenditure total-benefits
    set pension-balance pension-balance - total-benefits
  ]

  ;; ===== 4. pension growth =====
  let new-balance [pension-balance] of one-of governments

  ;; ---- 季度增长率 ----
  ifelse prev-balance > 0
  [
    set pension-growth (new-balance - prev-balance) / prev-balance
  ]
  [
    set pension-growth 0
  ]

  ;; ---- 年度增长率(每年末记录) ----
  if ticks mod 4 = 3 [
    ifelse previous-year-pension-balance > 0
    [
      set annual-pension-growth
        (new-balance - previous-year-pension-balance)
        / previous-year-pension-balance
    ]
    [
      set annual-pension-growth 0
    ]
    set previous-year-pension-balance new-balance
  ]


end



to update-statistics
  let temp-cpi cpi
  let young-workers households with [age <= youth-age-limit and age < retirement-age]
  let old-workers households with [age > youth-age-limit and age < retirement-age]
  let unemployed-young young-workers with [not employed?]
  let unemployed-old old-workers with [not employed?]
  let total-unemployed households with [age < retirement-age and not employed?]
  set young-unemployment ifelse-value (count young-workers > 0)
    [count unemployed-young / count young-workers] [0]
  set old-unemployment ifelse-value (count old-workers > 0)
    [count unemployed-old / count old-workers] [0]
  set total-unemployment ifelse-value (count young-workers + count old-workers > 0)
    [count total-unemployed / (count young-workers + count old-workers)] [0]

  let labour-force count households with [age < retirement-age]

  set vacancy-rate ifelse-value (labour-force > 0)
    [total-vacancies / labour-force] [0]
  let n ticks + 1
  set avg-young-unemployment ((n - 1) * avg-young-unemployment + young-unemployment) / n
  set avg-old-unemployment ((n - 1) * avg-old-unemployment + old-unemployment) / n
  let employed-households households with [employed?]
  set average-wage ifelse-value (count employed-households > 0)
    [mean [income / (1 - tau-w / 2)] of employed-households] [0]
  set avg-income mean [income] of households
  set total-workers count households with [age < retirement-age]
  set household-count count households


  ;; Okun variables
set gdp-growth 0
if previous-real-gdp > 0 [
  set gdp-growth (real-gdp - previous-real-gdp) / previous-real-gdp
]

set delta-unemployment total-unemployment - previous-unemployment

set previous-real-gdp real-gdp
set previous-unemployment total-unemployment
end

to-report tanh [x]
  ifelse abs x > 20 [
    report ifelse-value (x > 0) [1] [-1]
  ] [
    report (exp(x) - exp(- x)) / (exp(x) + exp(- x))
  ]
end

to plot-age-distribution-histogram
  set-current-plot "Age Distribution"
  clear-plot
  set-plot-x-range 0 90
  set-plot-y-range 0 150
  set-histogram-num-bars 10
  let age-list []
  ask households [
    let actual-age min list (int (age / 4)) (max-lifespan / 4)
    set age-list lput actual-age age-list
  ]
  histogram age-list
end

to plot-consumption-by-age-histogram
  set-current-plot "Avg Consumption by Age Groups"
  clear-plot
  set-plot-x-range 0 90
  set-plot-y-range 0 6
  set-histogram-num-bars 10
  let age-avg-consumption-list []
  let age-bins n-values 10 [0]
  let age-counts n-values 10 [0]
  ask households [
    let age-bin min list (int (age / 40)) 9
    set age-bins replace-item age-bin age-bins (item age-bin age-bins + actual-consumption)
    set age-counts replace-item age-bin age-counts (item age-bin age-counts + 1)
  ]
  let bin-index 0
  repeat 10 [
    let avg-consumption 0
    if item bin-index age-counts > 0 [
      set avg-consumption (item bin-index age-bins) / (item bin-index age-counts)
    ]
    let weight max list 1 (int (avg-consumption / 5))
    repeat weight [
      set age-avg-consumption-list lput (bin-index * 9) age-avg-consumption-list
    ]
    set bin-index bin-index + 1
  ]
  histogram age-avg-consumption-list
end



;may god unite-us-in-heaven
@#$#@#$#@
GRAPHICS-WINDOW
210
22
647
460
-1
-1
13.0
1
10
1
1
1
0
1
1
1
-16
16
-16
16
0
0
1
ticks
30.0

BUTTON
3
71
69
104
NIL
setup
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
73
71
136
104
NIL
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

PLOT
4
163
204
326
Average Age
NIL
NIL
0.0
10.0
25.0
40.0
true
false
"" ""
PENS
"average age" 1.0 0 -16777216 true "" "plot mean [age] of households / 4"

MONITOR
114
267
201
312
Average Age
mean [age] of households / 4
2
1
11

BUTTON
140
71
203
104
NIL
go
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

MONITOR
135
329
194
374
Retired
count households with [age >= retirement-age]
17
1
11

MONITOR
13
329
70
374
Young
count households with [age <= 80]
17
1
11

MONITOR
74
329
132
374
old
count households with [age > 80 and age < retirement-age]
17
1
11

PLOT
846
462
1057
612
Nominal gdp
NIL
NIL
0.0
45.0
1400.0
2100.0
true
false
"" ""
PENS
"N-gdp" 1.0 0 -16777216 true "" "plot nominal-gdp"

PLOT
845
614
1054
766
Real gdp
NIL
NIL
0.0
45.0
1400.0
2100.0
true
false
"" ""
PENS
"R-gdp" 1.0 0 -16777216 true "" "plot real-gdp"

MONITOR
216
122
413
167
total unemployed
count households with [age < retirement-age and employed? = false]
17
1
11

PLOT
655
189
1059
459
production, sale & inventories
NIL
NIL
0.0
45.0
0.0
2050.0
true
true
"" ""
PENS
"prodc" 1.0 0 -16777216 true "" "plot sum [production] of firms "
"sales" 1.0 0 -7500403 true "" "plot sum [sales] of firms"
"demand" 1.0 0 -12345184 true "" "plot total-demand"
"target" 1.0 0 -3508570 true "" "plot sum[production-target] of firms"
"capacity" 1.0 0 -955883 true "" "plot sum[production-capacity] of firms"
"inventories" 1.0 0 -2674135 true "" "plot sum[inventories] of firms"

MONITOR
844
592
918
637
R-gdp
real-gdp
2
1
11

MONITOR
975
376
1039
421
sales
sum [sales] of firms
0
1
11

MONITOR
975
330
1059
375
production
sum [production] of firms
0
1
11

PLOT
212
464
532
614
Unemployment
Tick
Rate
0.0
10.0
0.0
0.1
true
false
"" ""
PENS
"une%" 1.0 0 -12087248 true "" "plot total-unemployment"
"real" 1.0 0 -955883 true "" "if ticks <= 39 [plot item ticks real-unemp]"

MONITOR
846
442
923
487
N-gdp
nominal-gdp
2
1
11

MONITOR
244
463
309
508
Unemp%
total-unemployment * 100
2
1
11

PLOT
533
464
841
617
Inflation
NIL
NIL
0.0
10.0
-0.015
0.02
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot (cpi - previous-cpi) / previous-cpi"
"pen-1" 1.0 0 -955883 true "" "if ticks <= 39 [plot item ticks real-inflation / 100]"

MONITOR
523
528
581
573
Inf
(cpi - previous-cpi) / previous-cpi
2
1
11

PLOT
655
23
853
183
Pension balance
NIL
NIL
0.0
10.0
4700.0
6800.0
true
false
"" ""
PENS
"" 1.0 0 -10899396 true "" "plot sum [pension-balance] of governments"

PLOT
533
618
842
767
Bankruptcy
Tick
Count
0.0
10.0
0.0
3.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot bankruptcies-this-tick"

MONITOR
568
619
647
664
Bankruptcy
bankruptcies-this-tick
17
1
11

MONITOR
742
43
849
88
PAYGO Balance
sum [pension-balance] of governments
2
1
11

TEXTBOX
8
26
223
77
Run 40 ticks, 10 years in reality
14
0.0
1

MONITOR
216
75
413
120
active firms
count firms with [credit-rating >= default-tolerance ]
0
1
11

CHOOSER
4
113
204
158
simulation-period
simulation-period
"1994-2003" "2009-2018" "1994-2003 uniform" "1994-2003 India" "1994-2003 China" "1994-2003 Finland"
1

CHOOSER
4
165
204
210
run-mode
run-mode
"historical (40 ticks)" "long-run theory check (200 ticks)"
0

MONITOR
13
379
195
424
Elderly Dependency Ratio*
count households with [age >= 200] / count households with [age < 200]
2
1
11

MONITOR
216
28
336
73
Household Total
count households
17
1
11

TEXTBOX
15
427
195
482
*这里elderly的定义是>=65岁。但是实际上1994-2003退休年龄60岁，2009-2018退休年龄65岁。
11
0.0
1

INPUTBOX
18
474
168
534
n*
4.0
1
0
Number

TEXTBOX
22
539
210
562
这里的n* 是人口/公司数量放大倍数
11
0.0
1

MONITOR
216
170
413
215
total employed
count households with [age < retirement-age and employed? = true]
0
1
11

PLOT
7
615
207
765
total loans
NIL
NIL
0.0
10.0
2340.0
10.0
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot sum [debt] of firms "

MONITOR
18
567
97
612
total loans
sum [debt] of firms
2
1
11

MONITOR
338
28
413
73
Firm Total
count firms
17
1
11

MONITOR
215
218
318
263
适龄劳动力人数
count households with [age < retirement-age]
17
1
11

MONITOR
323
218
415
263
失业率
count households with [age < retirement-age and employed? = false] / count households with [age < retirement-age]
4
1
11

INPUTBOX
1430
603
1580
667
price-adjustments
0.01
1
0
Number

PLOT
1255
27
1452
187
zombie firms
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"zombie" 1.0 0 -16777216 true "" "plot count firms with [profits < 0]"

MONITOR
215
264
310
309
NIL
vacancy-rate
4
1
11

MONITOR
215
310
358
355
NIL
delta-unemployment
4
1
11

INPUTBOX
1264
230
1414
291
consumer-choices
4.0
1
0
Number

INPUTBOX
1264
294
1414
355
job-applications
4.0
1
0
Number

MONITOR
114
567
196
612
NIL
loan-index
4
1
11

PLOT
855
24
1055
186
pension-growth
NIL
NIL
0.0
10.0
-0.1
0.1
false
false
"" ""
PENS
"simulated" 1.0 0 -16777216 true "" "if ticks mod 4 = 3  [let year-index (ticks - 3) / 4  if year-index < length real-pension-growth [ plotxy (year-index - 1) annual-pension-growth]]"
"real" 1.0 0 -955883 true "" "if ticks mod 4 = 3  [let year-index (ticks - 3) / 4 if year-index < length real-pension-growth [ plotxy year-index (item year-index real-pension-growth)]]"

PLOT
1065
25
1250
187
Pension in&out
NIL
NIL
0.0
10.0
0.0
10.0
true
false
"" ""
PENS
"contribution" 1.0 0 -16777216 true "" "plot pension-contributions"
"benefits" 1.0 0 -7500403 true "" "plot pension-benefits"

PLOT
213
618
532
768
real gdp growth
NIL
NIL
0.0
10.0
0.0
0.05
true
false
"" ""
PENS
"default" 1.0 0 -16777216 true "" "plot gdp-growth"
"pen-1" 1.0 0 -955883 true "" "if ticks <= 39 [plot item ticks real-rgdp-growth]"

INPUTBOX
1073
418
1225
478
retirement-ages
181.0
1
0
Number

INPUTBOX
1430
229
1580
289
mpc-income
0.85
1
0
Number

INPUTBOX
1430
292
1580
352
mpc-wealth
0.05
1
0
Number

INPUTBOX
1430
354
1579
414
reorganization-prob
0.95
1
0
Number

INPUTBOX
1073
755
1225
815
paygo-rate-scale
1.0
1
0
Number

TEXTBOX
1257
210
1445
233
Category II (count-shift) 5
11
0.0
1

INPUTBOX
1265
359
1417
419
credit-thre
0.4
1
0
Number

INPUTBOX
1265
422
1415
482
default-tole
0.3
1
0
Number

INPUTBOX
1430
414
1580
474
profit-tax-rate
0.05
1
0
Number

INPUTBOX
1430
479
1580
539
credit-memory-window
20.0
1
0
Number

INPUTBOX
1265
484
1415
544
debt-repayment-rate
0.03
1
0
Number

INPUTBOX
1430
542
1580
602
contract-length
20.0
1
0
Number

INPUTBOX
1073
502
1223
562
death-prob-shift
1.0
1
0
Number

TEXTBOX
1347
364
1419
383
越大越难贷款
11
0.0
1

TEXTBOX
1345
429
1418
453
越大越难存活
11
0.0
1

INPUTBOX
1430
668
1580
728
production-adjustment
0.01
1
0
Number

INPUTBOX
1430
733
1580
793
target-cap-multiplier
1.4
1
0
Number

TEXTBOX
1597
208
1785
231
Category III (require calibration)
11
0.0
1

INPUTBOX
1605
229
1755
289
ini-price-level
1.15
1
0
Number

INPUTBOX
1605
293
1755
353
ini-production-level
15.0
1
0
Number

INPUTBOX
1605
357
1755
417
wealth-tax-cap
0.1
1
0
Number

TEXTBOX
1064
209
1252
232
Category I (count-shift) 4
11
0.0
1

INPUTBOX
1073
565
1242
625
productivity-growth-scale
1.0
1
0
Number

INPUTBOX
1073
630
1223
690
wage-growth-scale
1.0
1
0
Number

INPUTBOX
1073
230
1223
290
birth-count-shift
0.0
1
0
Number

INPUTBOX
1073
693
1223
753
pension-replace-scale
0.6
1
0
Number

INPUTBOX
1073
293
1223
353
deposit-rate-shift
0.0
1
0
Number

INPUTBOX
1073
355
1223
415
lend-rate-shift
0.0
1
0
Number

TEXTBOX
1423
212
1611
235
Category II (rate-scale) 8
11
0.0
1

TEXTBOX
1064
484
1252
507
Category I (rate-scale) 5
11
0.0
1

@#$#@#$#@
## WHAT IS IT?

(a general understanding of what the model is trying to show or explain)

## HOW IT WORKS

(what rules the agents use to create the overall behavior of the model)

## HOW TO USE IT

(how to use the model, including a description of each of the items in the Interface tab)

## THINGS TO NOTICE

(suggested things for the user to notice while running the model)

## THINGS TO TRY

(suggested things for the user to try to do (move sliders, switches, etc.) with the model)

## EXTENDING THE MODEL

(suggested things to add or change in the Code tab to make the model more complicated, detailed, accurate, etc.)

## NETLOGO FEATURES

(interesting or unusual features of NetLogo that the model uses, particularly in the Code tab; or where workarounds were needed for missing features)

## RELATED MODELS

(models in the NetLogo Models Library and elsewhere which are of related interest)

## CREDITS AND REFERENCES

(a reference to the model's URL on the web if it has one, as well as any other necessary credits, citations, and links)
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

building institution
false
0
Rectangle -7500403 true true 0 60 300 270
Rectangle -16777216 true false 130 196 168 256
Rectangle -16777216 false false 0 255 300 270
Polygon -7500403 true true 0 60 150 15 300 60
Polygon -16777216 false false 0 60 150 15 300 60
Circle -1 true false 135 26 30
Circle -16777216 false false 135 25 30
Rectangle -16777216 false false 0 60 300 75
Rectangle -16777216 false false 218 75 255 90
Rectangle -16777216 false false 218 240 255 255
Rectangle -16777216 false false 224 90 249 240
Rectangle -16777216 false false 45 75 82 90
Rectangle -16777216 false false 45 240 82 255
Rectangle -16777216 false false 51 90 76 240
Rectangle -16777216 false false 90 240 127 255
Rectangle -16777216 false false 90 75 127 90
Rectangle -16777216 false false 96 90 121 240
Rectangle -16777216 false false 179 90 204 240
Rectangle -16777216 false false 173 75 210 90
Rectangle -16777216 false false 173 240 210 255
Rectangle -16777216 false false 269 90 294 240
Rectangle -16777216 false false 263 75 300 90
Rectangle -16777216 false false 263 240 300 255
Rectangle -16777216 false false 0 240 37 255
Rectangle -16777216 false false 6 90 31 240
Rectangle -16777216 false false 0 75 37 90
Line -16777216 false 112 260 184 260
Line -16777216 false 105 265 196 265

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

factory
false
0
Rectangle -7500403 true true 76 194 285 270
Rectangle -7500403 true true 36 95 59 231
Rectangle -16777216 true false 90 210 270 240
Line -7500403 true 90 195 90 255
Line -7500403 true 120 195 120 255
Line -7500403 true 150 195 150 240
Line -7500403 true 180 195 180 255
Line -7500403 true 210 210 210 240
Line -7500403 true 240 210 240 240
Line -7500403 true 90 225 270 225
Circle -1 true false 37 73 32
Circle -1 true false 55 38 54
Circle -1 true false 96 21 42
Circle -1 true false 105 40 32
Circle -1 true false 129 19 42
Rectangle -7500403 true true 14 228 78 270

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.4.0
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
<experiments>
  <experiment name="scaling" repetitions="100" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <metric>mean [age] of households / 4</metric>
    <metric>count households with [age &gt;= 200] / count households with [age &lt; 200]</metric>
    <metric>total-unemployment</metric>
    <metric>delta-unemployment</metric>
    <metric>young-unemployment</metric>
    <metric>old-unemployment</metric>
    <metric>Inflation</metric>
    <metric>vacancy-rate</metric>
    <metric>gdp-growth</metric>
    <metric>loan-index</metric>
    <metric>bankruptcies-this-tick</metric>
    <metric>sum [pension-balance] of governments</metric>
    <metric>annual-pension-growth</metric>
    <metric>median [leverage] of firms</metric>
    <metric>mean [price] of firms</metric>
    <metric>mean [productivity] of firms</metric>
    <metric>mean [wage-offer] of firms</metric>
    <metric>sum [savings] of households / count households</metric>
    <metric>sum [production-capacity] of firms / count households</metric>
    <metric>mean [income] of households with [employed?]</metric>
    <metric>count households</metric>
    <metric>count firms</metric>
    <metric>sum [savings] of households</metric>
    <runMetricsCondition>ticks &gt;= 1</runMetricsCondition>
    <enumeratedValueSet variable="n*">
      <value value="1"/>
      <value value="2"/>
      <value value="4"/>
      <value value="8"/>
      <value value="16"/>
      <value value="32"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="1994-2003" repetitions="100" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <metric>mean [age] of households / 4</metric>
    <metric>count households with [age &gt;= 200] / count households with [age &lt; 200]</metric>
    <metric>total-unemployment</metric>
    <metric>delta-unemployment</metric>
    <metric>young-unemployment</metric>
    <metric>old-unemployment</metric>
    <metric>Inflation</metric>
    <metric>vacancy-rate</metric>
    <metric>gdp-growth</metric>
    <metric>loan-index</metric>
    <metric>bankruptcies-this-tick</metric>
    <metric>sum [pension-balance] of governments</metric>
    <metric>annual-pension-growth</metric>
    <metric>median [leverage] of firms</metric>
    <metric>mean [price] of firms</metric>
    <metric>mean [productivity] of firms</metric>
    <metric>mean [wage-offer] of firms</metric>
    <metric>sum [savings] of households / count households</metric>
    <metric>sum [production-capacity] of firms / count households</metric>
    <metric>mean [income] of households with [employed?]</metric>
    <metric>count households</metric>
    <metric>count firms</metric>
    <metric>sum [savings] of households</metric>
    <runMetricsCondition>ticks &gt;= 1</runMetricsCondition>
    <enumeratedValueSet variable="deposit-rate-shift">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="profit-tax-rate">
      <value value="0.05"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="run-mode">
      <value value="&quot;historical (40 ticks)&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="death-prob-shift">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="mpc-wealth">
      <value value="0.05"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="production-adjustment">
      <value value="0.01"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="mpc-income">
      <value value="0.85"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="n*">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="consumer-choices">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="pension-replace-scale">
      <value value="0.6"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ini-production-level">
      <value value="15"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="birth-count-shift">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="price-adjustments">
      <value value="0.01"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="job-applications">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lend-rate-shift">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="debt-repayment-rate">
      <value value="0.03"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="credit-thre">
      <value value="0.4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="contract-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="target-cap-multiplier">
      <value value="1.4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="credit-memory-window">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="productivity-growth-scale">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="wage-growth-scale">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="simulation-period">
      <value value="&quot;1994-2003&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ini-price-level">
      <value value="1.15"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="retirement-ages">
      <value value="181"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="wealth-tax-cap">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="default-tole">
      <value value="0.3"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="reorganization-prob">
      <value value="0.95"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="paygo-rate-scale">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="2009-2018" repetitions="100" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <metric>mean [age] of households / 4</metric>
    <metric>count households with [age &gt;= 200] / count households with [age &lt; 200]</metric>
    <metric>total-unemployment</metric>
    <metric>delta-unemployment</metric>
    <metric>young-unemployment</metric>
    <metric>old-unemployment</metric>
    <metric>Inflation</metric>
    <metric>vacancy-rate</metric>
    <metric>gdp-growth</metric>
    <metric>loan-index</metric>
    <metric>bankruptcies-this-tick</metric>
    <metric>sum [pension-balance] of governments</metric>
    <metric>annual-pension-growth</metric>
    <metric>median [leverage] of firms</metric>
    <metric>mean [price] of firms</metric>
    <metric>mean [productivity] of firms</metric>
    <metric>mean [wage-offer] of firms</metric>
    <metric>sum [savings] of households / count households</metric>
    <metric>sum [production-capacity] of firms / count households</metric>
    <metric>mean [income] of households with [employed?]</metric>
    <metric>count households</metric>
    <metric>count firms</metric>
    <metric>sum [savings] of households</metric>
    <runMetricsCondition>ticks &gt;= 1</runMetricsCondition>
    <enumeratedValueSet variable="deposit-rate-shift">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="profit-tax-rate">
      <value value="0.05"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="run-mode">
      <value value="&quot;historical (40 ticks)&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="death-prob-shift">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="mpc-wealth">
      <value value="0.05"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="production-adjustment">
      <value value="0.01"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="mpc-income">
      <value value="0.85"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="n*">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="consumer-choices">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="pension-replace-scale">
      <value value="0.6"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ini-production-level">
      <value value="16"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="birth-count-shift">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="price-adjustments">
      <value value="0.01"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="job-applications">
      <value value="4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="lend-rate-shift">
      <value value="0"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="debt-repayment-rate">
      <value value="0.03"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="credit-thre">
      <value value="0.4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="contract-length">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="target-cap-multiplier">
      <value value="1.4"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="credit-memory-window">
      <value value="20"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="productivity-growth-scale">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="wage-growth-scale">
      <value value="1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="simulation-period">
      <value value="&quot;2009-2018&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="ini-price-level">
      <value value="1.15"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="retirement-ages">
      <value value="181"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="wealth-tax-cap">
      <value value="0.1"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="default-tole">
      <value value="0.3"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="reorganization-prob">
      <value value="0.95"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="paygo-rate-scale">
      <value value="1"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="default tolerance" repetitions="100" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <metric>mean [age] of households / 4</metric>
    <metric>count households with [age &gt;= 200] / count households with [age &lt; 200]</metric>
    <metric>total-unemployment</metric>
    <metric>delta-unemployment</metric>
    <metric>young-unemployment</metric>
    <metric>old-unemployment</metric>
    <metric>Inflation</metric>
    <metric>vacancy-rate</metric>
    <metric>gdp-growth</metric>
    <metric>loan-index</metric>
    <metric>bankruptcies-this-tick</metric>
    <metric>sum [pension-balance] of governments</metric>
    <metric>annual-pension-growth</metric>
    <metric>median [leverage] of firms</metric>
    <runMetricsCondition>ticks &gt;= 1</runMetricsCondition>
    <enumeratedValueSet variable="default-tole">
      <value value="0.1"/>
      <value value="0.2"/>
      <value value="0.4"/>
      <value value="0.5"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="consumer choices" repetitions="100" sequentialRunOrder="false" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <metric>mean [age] of households / 4</metric>
    <metric>count households with [age &gt;= 200] / count households with [age &lt; 200]</metric>
    <metric>total-unemployment</metric>
    <metric>delta-unemployment</metric>
    <metric>young-unemployment</metric>
    <metric>old-unemployment</metric>
    <metric>Inflation</metric>
    <metric>vacancy-rate</metric>
    <metric>gdp-growth</metric>
    <metric>loan-index</metric>
    <metric>bankruptcies-this-tick</metric>
    <metric>sum [pension-balance] of governments</metric>
    <metric>annual-pension-growth</metric>
    <metric>median [leverage] of firms</metric>
    <runMetricsCondition>ticks &gt;= 1</runMetricsCondition>
    <enumeratedValueSet variable="consumer-choices">
      <value value="2"/>
      <value value="3"/>
      <value value="5"/>
      <value value="6"/>
    </enumeratedValueSet>
  </experiment>
  <experiment name="job applications" repetitions="100" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <metric>mean [age] of households / 4</metric>
    <metric>count households with [age &gt;= 200] / count households with [age &lt; 200]</metric>
    <metric>total-unemployment</metric>
    <metric>delta-unemployment</metric>
    <metric>young-unemployment</metric>
    <metric>old-unemployment</metric>
    <metric>Inflation</metric>
    <metric>vacancy-rate</metric>
    <metric>gdp-growth</metric>
    <metric>loan-index</metric>
    <metric>bankruptcies-this-tick</metric>
    <metric>sum [pension-balance] of governments</metric>
    <metric>annual-pension-growth</metric>
    <metric>median [leverage] of firms</metric>
    <runMetricsCondition>ticks &gt;= 1</runMetricsCondition>
    <enumeratedValueSet variable="job-applications">
      <value value="2"/>
      <value value="3"/>
      <value value="5"/>
      <value value="6"/>
    </enumeratedValueSet>
  </experiment>
</experiments>
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
