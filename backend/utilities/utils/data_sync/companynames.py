import random
import re
from typing import Dict, List, Optional


class CompanyNameGenerator:

    """A lightweight, efficient library for generating corporate company names with extensive vocabulary."""

    _vocab: Dict[str, List[str]] = {
        'prefixes': [
            'Star', 'Vision', 'Pulse', 'Core', 'Prime', 'Nova', 'Apex', 'Beacon', 'Spark',
            'Global', 'Innovate', 'Dynamic', 'Vantage', 'Horizon', 'Focus', 'Vertex', 'Nexus',
            'Clarity', 'Radiant', 'Insight', 'Pinnacle', 'Strive', 'Fusion', 'Vital', 'Zenith',
            'Echo', 'Stream', 'Vivid', 'Crest', 'Momentum', 'Signal', 'Trend', 'Glint', 'Wave',
            'Scope', 'Arc', 'Vibe', 'Frame', 'Lens', 'Bright', 'Summit', 'Edge', 'Origin',
            'Glimmer', 'Halo', 'Rise', 'Quest', 'Ignite', 'Surge', 'Vector', 'Clarity', 'Dawn',
            'Story', 'Pixel', 'Channel', 'Vitality', 'Precision', 'Catalyst', 'Flow', 'Vista',
            'Motion', 'Globe', 'Narrative', 'Spotlight', 'Power', 'Energy', 'Health', 'Bio',
            'Tech', 'Finance', 'Capital', 'Secure', 'Trust', 'Advance', 'Pioneer', 'Elite',
            'Next', 'Pro', 'Smart', 'Clear', 'True', 'Bold', 'Future', 'Peak', 'Unity',
            'Balance', 'Excel', 'Verve', 'Insightful', 'Radiance', 'Harmony', 'Meridian',
            'Optima', 'Vanguard', 'Keystone', 'Legacy', 'Forge', 'Grid', 'Circuit', 'Anchor'
        ],
        'bases': [
            'Tech', 'Systems', 'Solutions', 'Group', 'Partners', 'Ventures', 'Innovations',
            'Enterprises', 'Technologies', 'Dynamics', 'Labs', 'Consulting', 'Analytics',
            'Networks', 'Holdings', 'Associates', 'Collective', 'Alliance', 'Syndicate',
            'Consortium', 'Works', 'Hub', 'Forge', 'Foundry', 'Core', 'Matrix', 'Platform',
            'Bridge', 'Link', 'Nexus', 'Circuit', 'Pulse', 'Stream', 'Wave', 'Flow', 'Grid',
            'Cluster', 'Beacon', 'Channel', 'Conduit', 'Frame', 'Fusion', 'Path', 'Route',
            'Spark', 'Tide', 'Vortex', 'Axis', 'Base', 'Crest', 'Drift', 'Edge', 'Force',
            'Gauge', 'Haven', 'Kernel', 'Locus', 'Orbit', 'Peak', 'Quest', 'Riser', 'Scope',
            'Surge', 'Trace', 'Vector', 'Zone', 'Arc', 'Bolt', 'Catalyst', 'Drive', 'Echo',
            'Flare', 'Gleam', 'Horizon', 'Ignition', 'Jolt', 'Keystone', 'Lever', 'Motion',
            'Nerve', 'Optic', 'Pinnacle', 'Questor', 'Radian', 'Shift', 'Sparkle', 'Traction',
            'Verve', 'Wavelength', 'Zenith', 'Anchor', 'Beam', 'Cipher', 'Dynamo', 'Echelon',
            'Facet', 'Glimmer', 'Halo', 'Inertia', 'Junction', 'Kinetix', 'Luminary',
            'Meridian', 'Node', 'Oasis', 'Paragon', 'Pulse', 'Quasar', 'Rush', 'Sentry',
            'Titan', 'Unity', 'Vantage', 'Warden', 'Xcel', 'Yield', 'Zest', 'Agora', 'Brio',
            'Celerity', 'Dawn', 'Epoch', 'Flux', 'Gala', 'Helix', 'Legacy', 'Mosaic', 'Nimbus',
            'Odyssey', 'Polaris', 'Sable', 'Tempest', 'Vapor', 'Zodiac', 'Luxor', 'SingaCore',
            'Qataris', 'BharatSys', 'IndusTech', 'NordicSys', 'SwissTech', 'KiwiLabs',
            'AussieNet', 'SeychellesHub', 'MauritiusWorks', 'BotswanaGroup', 'AlgerianSys',
            'NigerianTech', 'MoroccanLabs', 'Tunisian', 'GhanaianVentures', 'KenyanSys',
            'EmiratiNet', 'NipponTech', 'SeoulSys', 'IsraeliLabs', 'SaudiaGroup',
            'HongkongHub', 'Kuwaiti', 'PalauanWorks', 'NauruNet', 'FijianSys', 'SamoanTech',
            'VanuatuLabs', 'IrishGroup', 'DanishNet', 'DutchSys', 'SwedeTech', 'GermanicLabs',
            'AustrianHub', 'FinnishWorks', 'BahamianSys', 'BarbadosTech', 'Panamanian',
            'CostaGroup', 'MexicanLabs', 'DominicanNet', 'GuatemalanSys', 'SalvadorTech',
            'ChileanHub', 'Uruguayan', 'ArgentinianSys', 'BrazilianTech', 'ColombianLabs',
            'PeruvianNet', 'ParaguayanSys', 'BolivianHub', 'Ecuadorian', 'VenezuelanTech',
            'Atlantis', 'Borealis', 'Crimson', 'Delta', 'Eon', 'Fathom', 'Grail', 'Hercules',
            'Icarus', 'Jupiter', 'Karma', 'Lunar', 'Mythos', 'Neon', 'Oracle', 'Pegasus',
            'Renaissance', 'Solstice', 'Terra', 'Utopia', 'Vega', 'Xenith', 'Amethyst',
            'Cobalt', 'Dracon', 'Elysium', 'Fluxor', 'Glimpse', 'HORIZON', 'Inspirex'
        ],
        'suffixes': [
            'Inc', 'LLC', 'Corp', 'Co', 'Limited', 'Group', 'International', 'Solutions',
            'Media', 'Studios', 'Network', 'Productions', 'Entertainment', 'Publishing',
            'Broadcasting', 'News', 'Channel', 'Digital', 'Press', 'Communications',
            'Tech', 'Technologies', 'Systems', 'Innovations', 'Labs', 'Analytics',
            'Consulting', 'Finance', 'Capital', 'Bank', 'Investments', 'Wealth', 'Advisory',
            'Markets', 'Financial', 'Holdings', 'Industries', 'Manufacturing', 'Engineering',
            'Works', 'Energy', 'Power', 'Renewables', 'Utilities', 'Health', 'Care', 'Bio',
            'Pharma', 'Medical', 'LifeSciences', 'Diagnostics', 'Company', 'Corporation',
            'Partners', 'Associates', 'Alliance', 'Consortium', 'Ventures', 'Global',
            'Worldwide', 'Services', 'Strategies', 'Agency', 'Bureau', 'Collective',
            'Therapeutics', 'Clinic', 'Resources', 'Generation', 'Securities', 'Exchange',
            'Trust', 'Fund', 'Core', 'Stream', 'Wave', 'Hub', 'Circuit', 'Matrix', 'Link',
            'Quest', 'Edge', 'Vision', 'Scope', 'Beacon', 'Precision', 'Nexus', 'Legacy'
        ],
        'descriptors': [
            'Creative', 'Innovative', 'Trusted', 'Strategic', 'Dynamic', 'Visionary', 'Premier',
            'Smart', 'Global', 'Advanced', 'Reliable', 'Elite', 'Progressive', 'Pioneering',
            'Bold', 'Vibrant', 'Leading', 'Secure', 'Robust', 'Transformative', 'Insightful',
            'Future', 'Agile', 'Resilient', 'Precision', 'Vital', 'Sustainable', 'Powerful',
            'Caring', 'Connected', 'Inspired', 'Breakthrough', 'Authentic', 'Proven', 'Renowned',
            'Esteemed', 'Brilliant', 'Adaptive', 'Forward', 'Clear', 'Next', 'Optimal', 'Prime',
            'Radiant', 'Intuitive', 'Respected', 'Acclaimed', 'Celebrated', 'Streamlined',
            'CuttingEdge', 'Groundbreaking', 'Vision', 'SmartTech', 'HighTech', 'CoreTech',
            'GlobalMedia', 'Digital', 'CreativeContent', 'InnovativeTech', 'TrustedFinance',
            'SecureBanking', 'StrategicCapital', 'AdvancedManufacturing', 'RobustEngineering',
            'SustainableEnergy', 'VitalHealth', 'CaringPharma', 'ConnectedSystems',
            'ProgressiveLabs', 'BoldVentures', 'InspiredMedia', 'PrecisionAnalytics',
            'ReliableSolutions', 'AuthenticCare', 'ProvenSystems', 'RenownedNews',
            'EsteemedBroadcast', 'AcclaimedStudios', 'CelebratedDigital', 'DynamicPower',
            'SmartEnergy', 'EliteCare', 'PremierBio', 'VisionaryHealth', 'CreativeStream',
            'InnovativeProductions', 'TrustedWealth', 'SecureMarkets', 'RobustIndustries',
            'SustainablePower', 'VitalLife', 'CaringClinic', 'ConnectedTech', 'ProgressiveEnergy',
            'BoldMedia', 'InspiredFinance', 'PrecisionManufacturing', 'ReliableHealth',
            'AuthenticNews', 'ProvenTech', 'RenownedCapital', 'EsteemedEngineering',
            'AcclaimedEnergy', 'CelebratedCare', 'DynamicDigital', 'SmartSolutions'
        ]
    }

    _industries: Dict[str, List[str]] = {
        'consulting': [
            'McKinsey & Company', 'Boston Consulting Group', 'Bain & Company', 'Deloitte', 'PwC', 'EY', 'KPMG',
            'Accenture', 'Oliver Wyman', 'Strategy&', 'Booz Allen Hamilton', 'Capgemini', 'IBM Consulting',
            'Grant Thornton', 'FTI Consulting', 'Huron Consulting', 'Guidehouse', 'Alvarez & Marsal', 'LEK Consulting',
            'A.T. Kearney', 'Roland Berger', 'Mercer', 'ZS Associates', 'Putnam Associates', 'ClearView Healthcare Partners',
            'Navigant', 'Protiviti', 'Slalom', 'Cognizant', 'Tata Consultancy Services', 'Infosys Consulting', 'Wipro',
            'BearingPoint', 'PA Consulting', 'Sia Partners', 'Arthur D. Little', 'The Bridgespan Group', 'Gallup',
            'Gartner', 'Forrester', 'Frost & Sullivan', 'Nextera', 'Analysis Group', 'Cornerstone Research',
            'Charles River Associates', 'Korn Ferry', 'Heidrick & Struggles', 'Russell Reynolds', 'Egon Zehnder',
            'Spencer Stuart', 'Aon Hewitt', 'Towers Watson', 'Dalberg', 'Monitor Deloitte', 'Parthenon-EY',
            'North Highland', 'Hitachi Consulting', 'CGI', 'Avanade', 'West Monroe', 'RSM', 'BDO', 'Crowe',
            'Baker Tilly', 'CliftonLarsonAllen', 'Marcum', 'Ankura', 'FTI Delta', 'Kroll', 'AlixPartners',
            'Berkeley Research Group', 'Teneo', 'FTI Technology', 'HCLTech Consulting', 'Genpact', 'Atos',
            'DXC Technology', 'Sopra Steria', 'Perficient', 'Thoughtworks', 'Publicis Sapient', 'EPAM Systems',
            'Mastech Digital', 'Moss Adams', 'Plante Moran', 'CBIZ', 'Syntel', 'NTT Data Consulting',
            'Capco', 'Point B', 'The Hackett Group', 'Altran', 'Pega Systems Consulting', 'IQVIA Consulting',
            'Synechron', 'Avanir', 'MWA Consulting', 'QbD Group', 'Altman Solon', 'Simon-Kucher & Partners',
            'Kearney', 'OC&C Strategy Consultants', 'Bain Capability Network', 'BCG Gamma', 'McKinsey Digital',
            'Deloitte Digital', 'PwC Digital Services', 'EY-Parthenon', 'Accenture Strategy', 'Capgemini Invent',
            'Booz Allen Digital Solutions', 'KPMG Lighthouse', 'Grant Thornton Advisory', 'RSM Consulting',
            'Crowe Consulting', 'BDO Digital', 'Protiviti Digital', 'Navigant Consulting', 'Huron Digital',
            'Guidehouse Digital', 'FTI Strategic Communications', 'Teneo Strategy', 'Ankura Consulting',
            'Berkeley Research Group Advisory', 'AlixPartners Digital', 'Kroll Advisory', 'FTI Cybersecurity',
            'PA Consulting Innovation', 'Sia Partners Digital', 'Arthur D. Little Innovation', 'Dalberg Advisors',
            'Monitor Deloitte Digital', 'ZS Associates Digital', 'Putnam Associates Strategy', 'ClearView Strategy',
            'L.E.K. Life Sciences', 'Navigant Healthcare', 'Huron Strategy', 'Guidehouse Energy', 'Alvarez & Marsal Healthcare',
            'FTI Healthcare', 'Kroll Risk Consulting', 'Teneo Risk', 'Ankura Cybersecurity', 'Bain Digital',
            'BCG Digital Ventures', 'McKinsey Sustainability', 'Deloitte Sustainability', 'PwC Sustainability',
            'EY Sustainability', 'KPMG Climate Services', 'Accenture Sustainability', 'Capgemini Sustainability',
            'Booz Allen Sustainability', 'Grant Thornton Sustainability', 'RSM Sustainability', 'Crowe Sustainability',
            'BDO Sustainability', 'Protiviti Sustainability', 'Navigant Sustainability', 'Huron Sustainability',
            'Guidehouse Sustainability', 'FTI Energy', 'Teneo Energy', 'Ankura Energy', 'Kroll Energy',
            'AlixPartners Energy', 'Berkeley Research Group Energy', 'Altran Energy', 'PA Consulting Energy',
            'Sia Partners Energy', 'Arthur D. Little Energy', 'Dalberg Energy', 'Monitor Deloitte Energy',
            'ZS Associates Healthcare', 'Putnam Associates Healthcare', 'ClearView Life Sciences', 'L.E.K. Healthcare',
            'Navigant Energy', 'Huron Energy', 'Guidehouse Healthcare', 'Alvarez & Marsal Finance',
            'FTI Finance', 'Kroll Finance', 'Teneo Finance', 'Ankura Finance', 'AlixPartners Finance',
            'Berkeley Research Group Finance', 'Altran Technology', 'PA Consulting Technology', 'Sia Partners Technology',
            'Arthur D. Little Technology', 'Dalberg Technology', 'Monitor Deloitte Technology', 'ZS Associates Technology',
            'Putnam Associates Technology', 'ClearView Technology', 'L.E.K. Technology', 'Navigant Technology'
        ],
        'manufacturing': [
            'Siemens', 'General Electric', 'Boeing', 'Airbus', 'Toyota', 'Ford', 'General Motors', 'Honda',
            'Volkswagen', 'BMW', 'Mercedes-Benz', 'Tesla', 'Caterpillar', 'John Deere', 'Komatsu', 'Hitachi',
            'Hyundai Heavy Industries', 'Mitsubishi Heavy Industries', 'Volvo Group', 'CNH Industrial',
            'Kubota', 'Doosan', 'Sany Group', 'JCB', 'Terex', 'Liebherr', '3M', 'Honeywell', 'Lockheed Martin',
            'Northrop Grumman', 'Raytheon', 'BAE Systems', 'General Dynamics', 'Rolls-Royce', 'Safran',
            'Thales', 'Leonardo', 'Textron', 'Bombardier', 'Embraer', 'Dassault Aviation', 'ArcelorMittal',
            'Nippon Steel', 'POSCO', 'Baosteel', 'Tata Steel', 'JFE Steel', 'Nucor', 'Steel Dynamics',
            'Vale', 'BHP', 'Rio Tinto', 'Alcoa', 'Novelis', 'Constellium', 'Kaiser Aluminum', 'Dow Chemical',
            'DuPont', 'BASF', 'LyondellBasell', 'SABIC', 'Evonik', 'Covestro', 'Lanxess', 'Eastman Chemical',
            'Celanese', 'Solvay', 'Arkema', 'PPG Industries', 'Sherwin-Williams', 'Axalta', 'Valspar',
            'Corning', 'Saint-Gobain', 'Asahi Glass', 'Nippon Sheet Glass', 'Owens Corning', 'Johns Manville',
            ' Knauf', 'Kingspan', 'CRH', 'LafargeHolcim', 'HeidelbergCement', 'Cemex', 'Vulcan Materials',
            'Martin Marietta', 'Eagle Materials', 'Summit Materials', 'Boral', 'James Hardie', 'Tyson Foods',
            'Cargill', 'Archer Daniels Midland', 'Bunge', 'Sysco', 'Nestlé', 'Unilever', 'Mondelez',
            'Kraft Heinz', 'General Mills', 'Kellogg’s', 'Conagra Brands', 'Pepsico', 'Coca-Cola', 'Danone',
            'Mars', 'Ferrero', 'Hershey', 'Campbell Soup', 'JBS', 'BRF', 'Smithfield Foods', 'Hormel Foods',
            'Perdue Farms', 'Sanderson Farms', 'Pirelli', 'Michelin', 'Bridgestone', 'Goodyear', 'Continental',
            'Hankook', 'Sumitomo Rubber', 'Yokohama Rubber', 'Cooper Tire', 'Toyo Tire', 'Procter & Gamble',
            'Colgate-Palmolive', 'Kimberly-Clark', 'Clorox', 'Reckitt Benckiser', 'Henkel', 'Ecolab',
            'Church & Dwight', 'Estée Lauder', 'L’Oréal', 'Shiseido', 'Coty', 'Beiersdorf', 'Amcor',
            'Ball Corporation', 'Crown Holdings', 'Sealed Air', 'Berry Global', 'AptarGroup', 'WestRock',
            'International Paper', 'Smurfit Kappa', 'Mondi', 'DS Smith', 'Graphic Packaging', 'Sonoco',
            'Packaging Corporation of America', 'Oji Holdings', 'UPM-Kymmene', 'Stora Enso', 'Sappi',
            'Suzano', 'Klabin', 'Deere & Company', 'AGCO', 'Claas', 'Yanmar', 'Mahindra & Mahindra',
            'Escorts', 'SDF Group', 'Iseki', 'Kubota Tractor', 'Case IH', 'New Holland', 'Fiat Chrysler',
            'Stellantis', 'Renault', 'Nissan', 'Subaru', 'Mazda', 'Suzuki', 'Isuzu', 'Daimler', 'Paccar',
            'Navistar', 'Oshkosh', 'Manitowoc', 'Tadano', 'XCMG', 'Zoomlion', 'SANY Heavy Industry',
            'LiuGong', 'Lonking', 'Shantui', 'XGMA', 'Yutong', 'King Long', 'Higer Bus', 'BYD Auto',
            'Geely', 'Chery', 'Great Wall Motors', 'SAIC Motor', 'FAW Group', 'Dongfeng Motor'
        ],
        'energy': [
            'ExxonMobil', 'Chevron', 'Shell', 'BP', 'TotalEnergies', 'ConocoPhillips', 'Eni', 'Equinor',
            'Saudi Aramco', 'Petrobras', 'Sinopec', 'CNOOC', 'Gazprom', 'Rosneft', 'Lukoil', 'Enbridge',
            'TC Energy', 'Kinder Morgan', 'Williams Companies', 'Enterprise Products', 'Energy Transfer',
            'Magellan Midstream', 'ONEOK', 'Cheniere Energy', 'Sempra Energy', 'NextEra Energy',
            'Duke Energy', 'Southern Company', 'Dominion Energy', 'Exelon', 'American Electric Power',
            'PSEG', 'Consolidated Edison', 'Xcel Energy', 'Edison International', 'FirstEnergy', 'Eversource',
            'DTE Energy', 'Entergy', 'PPL Corporation', 'CenterPoint Energy', 'Atmos Energy', 'National Grid',
            'Fortis', 'Hydro One', 'Enel', 'Iberdrola', 'Engie', 'E.ON', 'RWE', 'Vattenfall', 'Orsted',
            'Vestas', 'Siemens Gamesa', 'GE Renewable Energy', 'Nordex', 'Goldwind', 'Enercon', 'Suzlon',
            'First Solar', 'SunPower', 'Canadian Solar', 'JinkoSolar', 'Trina Solar', 'Hanwha Q Cells',
            'LONGi Solar', 'JA Solar', 'Yingli Solar', 'Tesla Energy', 'Fluence', 'AES Corporation',
            'NRG Energy', 'Calpine', 'Vistra Energy', 'Invenergy', 'Pattern Energy', 'Avangrid',
            'Brookfield Renewable', 'Algonquin Power', 'TransAlta', 'Innergex', 'Boralex', 'Capital Power',
            'Schlumberger', 'Halliburton', 'Baker Hughes', 'Weatherford', 'TechnipFMC', 'Subsea 7',
            'Saipem', 'Wood Group', 'Petrofac', 'Worley', 'Fluor', 'Jacobs Engineering', 'KBR',
            'SNC-Lavalin', 'Bechtel', 'McDermott', 'Chiyoda Corporation', 'JGC Corporation', 'Toyo Engineering',
            'Aker Solutions', 'BW Offshore', 'Modec', 'SBM Offshore', 'TGS', 'PGS', 'CGG', 'Fugro',
            'Oceaneering', 'Helix Energy', 'Valaris', 'Transocean', 'Noble Corporation', 'Diamond Offshore',
            'Seadrill', 'Borr Drilling', 'Odfjell Drilling', 'Maersk Drilling', 'Shelf Drilling', 'Equinor Energy',
            'Repsol', 'OMV', 'MOL Group', 'Wintershall Dea', 'Neptune Energy', 'Kosmos Energy', 'Tullow Oil',
            'Occidental Petroleum', 'EOG Resources', 'Pioneer Natural Resources', 'Devon Energy', 'Marathon Oil',
            'APA Corporation', 'Hess Corporation', 'Murphy Oil', 'Chesapeake Energy', 'Southwestern Energy',
            'Antero Resources', 'EQT Corporation', 'Range Resources', 'Cabot Oil & Gas', 'Cimarex Energy',
            'Ovintiv', 'Talos Energy', 'Kosmos Energy', 'Santos', 'Woodside Petroleum', 'Oil Search',
            'Beach Energy', 'Origin Energy', 'AGL Energy', 'APA Group', 'AusNet Services', 'Spark Infrastructure',
            'TPI Composites', 'Clariant', 'Umicore', 'Johnson Matthey', 'Albemarle', 'SQM', 'Tianqi Lithium',
            'Ganfeng Lithium', 'Livent', 'Orocobre', 'Pilbara Minerals', 'Galaxy Resources', 'Allkem',
            'Imerys', 'Eramet', 'Glencore', 'Anglo American', 'Freeport-McMoRan', 'Southern Copper',
            'Antofagasta', 'First Quantum Minerals', 'Teck Resources', 'Hudbay Minerals', 'Lundin Mining',
            'Ivanhoe Mines', 'B2Gold', 'Newmont', 'Barrick Gold', 'Agnico Eagle', 'Kinross Gold',
            'Gold Fields', 'Harmony Gold', 'Yamana Gold', 'Eldorado Gold', 'Centerra Gold', 'Iamgold'
        ],
        'healthcare': [
            'UnitedHealth Group', 'CVS Health', 'Anthem', 'Cigna', 'Centene', 'Molina Healthcare', 'Humana',
            'Kaiser Permanente', 'HCA Healthcare', 'Tenet Healthcare', 'Universal Health Services', 'Community Health Systems',
            'Ascension Health', 'Providence Health', 'Dignity Health', 'Sutter Health', 'Mayo Clinic', 'Cleveland Clinic',
            'Johns Hopkins Medicine', 'Mass General Brigham', 'NYU Langone Health', 'UCLA Health', 'Cedars-Sinai',
            'Stanford Health Care', 'Banner Health', 'Advocate Aurora Health', 'Intermountain Healthcare', 'Scripps Health',
            'Northwell Health', 'Mount Sinai Health System', 'Baylor Scott & White Health', 'Bon Secours Mercy Health',
            'Geisinger Health', 'UPMC', 'Inova Health System', 'AdventHealth', 'Atrium Health', 'Novant Health',
            'Henry Ford Health System', 'Spectrum Health', 'Trinity Health', 'Mercy Health', 'Pfizer', 'Johnson & Johnson',
            'Merck & Co.', 'Gilead Sciences', 'Amgen', 'AbbVie', 'Bristol Myers Squibb', 'Eli Lilly', 'Novartis',
            'Roche', 'Sanofi', 'AstraZeneca', 'GlaxoSmithKline', 'Takeda Pharmaceutical', 'Moderna', 'BioNTech',
            'Regeneron', 'Vertex Pharmaceuticals', 'Biogen', 'Incyte', 'Alexion Pharmaceuticals', 'Illumina',
            'Intuitive Surgical', 'Stryker', 'Medtronic', 'Boston Scientific', 'Becton Dickinson', 'Zimmer Biomet',
            'Hologic', 'Dentsply Sirona', 'Varian Medical Systems', 'Edwards Lifesciences', 'ResMed', 'Dexcom',
            'Hologic', 'Align Technology', 'Teleflex', 'Steris', 'Baxter International', 'Fresenius Medical Care',
            'DaVita', 'Labcorp', 'Quest Diagnostics', 'Sonic Healthcare', 'Eurofins Scientific', 'Hologic',
            'PerkinElmer', 'Bio-Rad Laboratories', 'Waters Corporation', 'Agilent Technologies', 'Thermo Fisher Scientific',
            'Danaher', 'IQVIA', 'Syneos Health', 'PRA Health Sciences', 'Icon PLC', 'Charles River Laboratories',
            'WuXi AppTec', 'Covance', 'Parexel', 'Medpace', 'Sartorius', 'Lonza', 'Catalent', 'Patheon',
            'Siegfried', 'Recipharm', 'Alcami', 'Vetter Pharma', 'Jubilant Pharma', 'Dr. Reddy’s Laboratories',
            'Cipla', 'Sun Pharmaceutical', 'Lupin', 'Aurobindo Pharma', 'Torrent Pharmaceuticals', 'Zydus Cadila',
            'Glenmark Pharmaceuticals', 'Intas Pharmaceuticals', 'Alkem Laboratories', 'Mylan', 'Teva Pharmaceutical',
            'Sandoz', 'Hikma Pharmaceuticals', 'Perrigo', 'Endo International', 'Amneal Pharmaceuticals',
            'Viatris', 'Bausch Health', 'Jazz Pharmaceuticals', 'Horizon Therapeutics', 'UCB Pharma', 'Ipsen',
            'Grifols', 'CSL Limited', 'BioMarin Pharmaceutical', 'Sarepta Therapeutics', 'Alnylam Pharmaceuticals',
            'bluebird bio', 'Moderna Therapeutics', 'Novavax', 'Emergent BioSolutions', 'Dynavax Technologies',
            'Vaxart', 'Inovio Pharmaceuticals', 'Arcturus Therapeutics', 'CureVac', 'Translate Bio', 'Vir Biotechnology',
            'Adaptive Biotechnologies', '10x Genomics', 'Guardant Health', 'Invitae', 'Natera', 'Myriad Genetics',
            'Exact Sciences', 'Foundation Medicine', 'Caris Life Sciences', 'Tempus', 'Veracyte', 'Hologic',
            'Teladoc Health', 'Amwell', 'Hims & Hers Health', 'GoodRx', '1Life Healthcare', 'Oak Street Health',
            'VillageMD', 'One Medical', 'Livongo Health', 'Omada Health', 'Cerebral', 'Talkspace', 'Lyra Health',
            'Ginger', 'Headspace Health', 'Calm', 'Evernorth', 'Optum', 'Elevance Health', 'Blue Cross Blue Shield',
            'Aetna', 'WellCare', 'Magellan Health', 'Bright Health', 'Oscar Health', 'Clover Health', 'Alignment Healthcare'
        ],
        'finance': [
            'JPMorgan Chase', 'Bank of America', 'Wells Fargo', 'Citigroup', 'Goldman Sachs', 'Morgan Stanley',
            'Barclays', 'HSBC', 'Deutsche Bank', 'UBS', 'Credit Suisse', 'BNP Paribas', 'Société Générale',
            'Standard Chartered', 'Santander', 'BBVA', 'ING Group', 'UniCredit', 'Intesa Sanpaolo', 'Lloyds Banking Group',
            'Royal Bank of Canada', 'Toronto-Dominion Bank', 'Bank of Montreal', 'Scotiabank', 'CIBC', 'National Bank of Canada',
            'Commonwealth Bank', 'Westpac', 'ANZ Bank', 'National Australia Bank', 'Macquarie Group', 'DBS Bank',
            'OCBC Bank', 'UOB', 'Standard Bank', 'FirstRand', 'Nedbank', 'Absa Group', 'ICICI Bank', 'HDFC Bank',
            'State Bank of India', 'Axis Bank', 'Kotak Mahindra Bank', 'Yes Bank', 'IndusInd Bank', 'Bajaj Finance',
            'China Construction Bank', 'Industrial and Commercial Bank of China', 'Agricultural Bank of China',
            'Bank of China', 'Ping An Insurance', 'China Merchants Bank', 'China Minsheng Bank', 'Shanghai Pudong Development Bank',
            'BlackRock', 'Vanguard', 'State Street', 'Fidelity Investments', 'T. Rowe Price', 'Invesco', 'Franklin Templeton',
            'Schroders', 'Amundi', 'PIMCO', 'Capital Group', 'Northern Trust', 'BNY Mellon', 'Prudential Financial',
            'MetLife', 'AIG', 'Allianz', 'AXA', 'Zurich Insurance', 'Manulife', 'Sun Life Financial', 'Aviva',
            'Legal & General', 'Generali', 'Swiss Re', 'Munich Re', 'Hannover Re', 'SCOR', 'Chubb', 'Travelers',
            'Allstate', 'Progressive', 'Berkshire Hathaway', 'American Express', 'Visa', 'Mastercard', 'PayPal',
            'Square', 'Stripe', 'Adyen', 'Fiserv', 'Global Payments', 'Worldpay', 'Discover Financial', 'Synchrony Financial',
            'Capital One', 'American International Group', 'Hartford Financial', 'Principal Financial', 'Lincoln National',
            'Voya Financial', 'T Rowe Price', 'Edward Jones', 'Raymond James', 'LPL Financial', 'Ameriprise Financial',
            'Charles Schwab', 'E*Trade', 'TD Ameritrade', 'Interactive Brokers', 'Robinhood', 'Wealthfront', 'Betterment',
            'SoFi', 'LendingClub', 'Prosper', 'Affirm', 'Upstart', 'NerdWallet', 'Credit Karma', 'Intuit', 'H&R Block',
            'TurboTax', 'Moody’s', 'S&P Global', 'Fitch Ratings', 'Morningstar', 'MSCI', 'FactSet', 'Bloomberg LP',
            'Refinitiv', 'IHS Markit', 'Equifax', 'Experian', 'TransUnion', 'Dun & Bradstreet', 'Kroll Bond Rating Agency',
            'A.M. Best', 'Crisil', 'ICRA', 'Care Ratings', 'Bridgewater Associates', 'Two Sigma', 'Renaissance Technologies',
            'DE Shaw', 'Citadel', 'AQR Capital', 'Millennium Management', 'Elliott Management', 'Baupost Group',
            'Pershing Square', 'TPG Capital', 'Carlyle Group', 'KKR', 'Apollo Global Management', 'Blackstone',
            'Advent International', 'Bain Capital', 'Warburg Pincus', 'CVC Capital Partners', 'Hellman & Friedman',
            'Silver Lake', 'Vista Equity Partners', 'General Atlantic', 'Sequoia Capital', 'Andreessen Horowitz',
            'Accel Partners', 'Kleiner Perkins', 'Benchmark Capital', 'Founders Fund', 'Index Ventures', 'Lightspeed Venture Partners',
            'Greylock Partners', 'Battery Ventures', 'New Enterprise Associates', 'Tiger Global Management', 'SoftBank Vision Fund',
            'Temasek Holdings', 'GIC', 'Qatar Investment Authority', 'Abu Dhabi Investment Authority', 'Kuwait Investment Authority',
            'Public Investment Fund', 'Norges Bank Investment Management', 'Canada Pension Plan Investment Board',
            'Ontario Teachers’ Pension Plan', 'CalPERS', 'CalSTRS', 'TIAA', 'Fidelity International', 'Nomura Holdings',
            'Mizuho Financial Group', 'Sumitomo Mitsui Financial Group', 'MUFG Bank', 'Daiwa Securities', 'SBI Holdings'
        ],
        'tech': [
            'Apple', 'Microsoft', 'Amazon', 'Google', 'Meta', 'Tesla', 'NVIDIA', 'Intel', 'AMD', 'Qualcomm',
            'IBM', 'Oracle', 'SAP', 'Salesforce', 'Adobe', 'Cisco Systems', 'Dell Technologies', 'Hewlett Packard Enterprise',
            'HP Inc.', 'Lenovo', 'ASUS', 'Acer', 'Toshiba', 'Fujitsu', 'NEC', 'Hitachi', 'Sony', 'Samsung Electronics',
            'LG Electronics', 'Panasonic', 'TCL Technology', 'Xiaomi', 'Oppo', 'Vivo', 'Huawei', 'ZTE', 'Ericsson',
            'Nokia', 'Motorola Solutions', 'Arista Networks', 'Juniper Networks', 'Palo Alto Networks', 'Fortinet',
            'Check Point Software', 'Symantec', 'McAfee', 'CrowdStrike', 'Zscaler', 'Okta', 'ServiceNow', 'Workday',
            'Atlassian', 'Splunk', 'Datadog', 'Snowflake', 'Palantir Technologies', 'MongoDB', 'Elastic', 'Twilio',
            'UiPath', 'Automation Anywhere', 'Blue Prism', 'VMware', 'Red Hat', 'Citrix Systems', 'Nutanix',
            'Veeam Software', 'Commvault', 'Cohesity', 'Rubrik', 'NetApp', 'Pure Storage', 'Western Digital',
            'Seagate Technology', 'Micron Technology', 'Broadcom', 'Texas Instruments', 'Analog Devices', 'Skyworks Solutions',
            'Microchip Technology', 'NXP Semiconductors', 'STMicroelectronics', 'Infineon Technologies', 'ON Semiconductor',
            'Renesas Electronics', 'Arm Holdings', 'Cadence Design Systems', 'Synopsys', 'Ansys', 'Autodesk',
            'Bentley Systems', 'PTC', 'Dassault Systèmes', 'Intuit', 'Sage', 'Xero', 'Freshworks', 'Zoho Corporation',
            'HubSpot', 'Zendesk', 'Monday.com', 'Asana', 'Trello', 'Slack Technologies', 'Zoom Video Communications',
            'RingCentral', 'Five9', '8x8', 'Vonage', 'Dropbox', 'Box', 'Evernote', 'DocuSign', 'HelloSign',
            'Smartsheet', 'Airtable', 'Notion', 'Coda', 'GitHub', 'GitLab', 'Bitbucket', 'JetBrains', 'Unity Technologies',
            'Epic Games', 'Activision Blizzard', 'Electronic Arts', 'Take-Two Interactive', 'Ubisoft', 'Square Enix',
            'Bandai Namco', 'Tencent', 'NetEase', 'Baidu', 'Alibaba', 'JD.com', 'Pinduoduo', 'Meituan', 'ByteDance',
            'Kuaishou', 'Didi Chuxing', 'Ant Group', 'Paytm', 'PhonePe', 'Razorpay', 'CRED', 'Zomato', 'Swiggy',
            'Ola', 'Grab', 'Gojek', 'Lyft', 'Uber', 'Airbnb', 'Booking Holdings', 'Expedia Group', 'Tripadvisor',
            'Spotify', 'Tidal', 'Deezer', 'Cloudflare', 'Fastly', 'Akamai Technologies', 'F5 Networks', 'Imperva',
            'Dynatrace', 'New Relic', 'SolarWinds', 'AppDynamics', 'Snyk', 'JFrog', 'HashiCorp', 'Confluent',
            'MuleSoft', 'Tableau Software', 'Qlik', 'ThoughtSpot', 'Sisense', 'Looker', 'Domo', 'Alteryx',
            'Cloudera', 'Hortonworks', 'Teradata', 'Informatica', 'Talend', 'Matillion', 'Fivetran', 'Stitch',
            'SnapLogic', 'Boomi', 'Celonis', 'UiPath', 'Appian', 'Pega Systems', 'OutSystems', 'Mendix',
            'ServiceTitan', 'Procore Technologies', 'Toast', 'Shopify', 'BigCommerce', 'Wix', 'Squarespace',
            'Webflow', 'Bubble', 'WordPress', 'Drupal', 'Joomla', 'Magento', 'Salesforce Commerce Cloud',
            'Epicor', 'Infor', 'NetSuite', 'Syspro', 'Odoo', 'Zoho CRM', 'Pipedrive', 'Insightly', 'SugarCRM',
            'Freshsales', 'Stripe', 'Adyen', 'Braintree', 'Worldpay', 'Checkout.com', 'Klarna', 'Affirm'
        ],
        'media': [
            'Disney', 'Netflix', 'Comcast', 'WarnerMedia', 'ViacomCBS', 'SonyPictures',
            'UniversalStudios', 'FoxCorporation', 'BBC', 'CNN', 'NBCUniversal', 'ABC',
            'CBS', 'TheNewYorkTimes', 'TheWashingtonPost', 'Bloomberg', 'Reuters',
            'AssociatedPress', 'HearstCorporations', 'CondéNast', 'VoxMedia', 'BuzzFeed',
            'TheGuardian', 'NewsCorp', 'TimeWarner', 'DiscoveryInc', 'SinclairBroadcast',
            'iHeartMedia', 'Spotify', 'Pandora', 'HBO', 'Showtime', 'AMCNetworks',
            'Lionsgate', 'MGM', 'ParamountPictures', 'DreamWorksAnimation', 'A24',
            'SkyGroup', 'ITV', 'Channel4', 'ProSiebenSat1', 'Mediaset', 'TF1Group',
            'AlJazeera', 'TheWallStreetJournal', 'Gannett', 'McClatchy', 'TribunePublishing',
            'AxelSpringer', 'BauerMediaGroup', 'TheEconomist', 'Forbes', 'TimeInc',
            'ZiffDavis', 'MeredithCorporation', 'Dotdash', 'ViceMedia', 'TheAtlantic',
            'Politico', 'HuffPost', 'Slate', 'Salon', 'TheDailyBeast', 'ComplexNetworks',
            'PenskeMedia', 'RollingStone', 'Billboard', 'TheHollywoodReporter', 'Variety',
            'Deadline', 'EWTN', 'Telemundo', 'Univision', 'Globo', 'ZeeEntertainment',
            'StarIndia', 'SonyEntertainmentTelevision', 'NHK', 'FranceTélévisions',
            'RAI', 'ARD', 'ZDF', 'CBC', 'NineEntertainment', 'SevenWestMedia',
            'TenNetwork', 'Foxtel', 'Stan', 'Hulu', 'AmazonPrimeVideo', 'AppleTV',
            'YouTube', 'Twitch', 'Vimeo', 'Dailymotion', 'Tubi', 'Roku', 'PlutoTV',
            'Peacock', 'ESPN', 'TurnerBroadcasting', 'MTV', 'BET', 'VH1', 'CMT',
            'NationalGeographic', 'HistoryChannel', 'AandE', 'Lifetime', 'TLC',
            'FoodNetwork', 'HGTV', 'TravelChannel', 'AnimalPlanet', 'DiscoveryChannel',
            'SkyNews', 'Euronews', 'France24', 'DW', 'RT', 'CGTN', 'TRTWorld',
            'SiriusXM', 'CumulusMedia', 'Entercom', 'SalemMediaGroup',
            'Audacy', 'ClearChannel', 'TownsquareMedia', 'EmmisCommunications',
            'BeasleyBroadcast', 'WestwoodOne', 'PodcastOne', 'Wondery', 'Stitcher',
            'Acast', 'SoundCloud', 'Anchor', 'Libsyn', 'Buzzsprout', 'iHeartRadio',
            'Audible', 'Storytel', 'Scribd', 'Medium', 'Substack', 'Patreon',
            'OnlyFans', 'TikTok', 'Snapchat', 'Instagram', 'Meta', 'Twitter', 'Reddit',
            'Pinterest', 'LinkedIn', 'Quora', 'Tumblr', 'WordPress', 'Webflow',
            'Squarespace', 'Wix', 'Gizmodo', 'TechCrunch', 'Wired', 'Engadget',
            'TheVerge', 'CNET', 'ZDNet', 'Mashable', 'DigitalTrends', 'IGN',
            'GameSpot', 'Polygon', 'Kotaku', 'Eurogamer', 'RockPaperShotgun',
            'ScreenRant', 'Collider', 'IndieWire', 'RottenTomatoes', 'Fandango',
            'IMDb', 'Letterboxd', 'BleacherReport', 'SB Nation', 'TheRinger',
            'Eurosport', 'DAZN', 'Cheddar', 'NowThis', 'TheYoungTurks', 'BarstoolSports',
            'Refinery29', 'Bustle', 'EliteDaily', 'Mic', 'Upworthy', 'OzyMedia',
            'GroupNineMedia', 'Thrillist', 'PopSugar', 'Inverse', 'Futurism',
            'MorningBrew', 'TheSkimm', 'Axios', 'Semafor', 'TheInformation',
            'BusinessInsider', 'FastCompany', 'IncMagazine', 'Entrepreneur',
            'Scholastic', 'PenguinRandomHouse', 'HarperCollins', 'SimonSchuster',
            'HachetteBookGroup', 'MacmillanPublishers', 'Wiley', 'SpringerNature'
        ]
    }

    def __init__(self, seed: Optional[int] = None):
        """Initialize the generator with an optional random seed."""
        if seed is not None:
            random.seed(seed)
        self._recent_acronyms: set = set()

    def _supported_keys(self, key: Optional[str]) -> str:
        key = ['bs','ps','pb','rc']
        return random.choice(key)

    def generate_name(
        self,
        format_type: str = 'standard',
        industry: Optional[str] = None,
        descriptor: bool = False,
        acronym: bool = False,
        org: Optional[str] = None
    ) -> str:
        """
        Generate a company name based on specified parameters.

        Args:
            format_type: One of 'standard', 'short', 'complex', 'modern'
            industry: Optional industry for specific naming (e.g., 'tech', 'finance')
            descriptor: Include a descriptor like 'Advanced'
            acronym: Generate an acronym-based name
            name_generator: Optional name generator type ('bs', 'ps', 'pb', 'rc')

        Returns:
            A generated company name with spaces between components

        Raises:
            ValueError: If invalid format_type, industry, or name_generator

        """
        if format_type not in {'standard', 'short', 'complex', 'modern'}:
            raise ValueError("format_type must be one of: standard, short, complex, modern")
        if industry and industry not in self._industries:
            raise ValueError(f"Invalid industry. Must be one of: {list(self._industries.keys())}")

        if acronym:
            return self._generate_acronym_name(industry)

        if org:
            name_generators = {
                'bs': self._get_random_base_suffix_name,
                'ps': self._get_random_prefix_suffix_name,
                'pb': self._get_random_prefix_base_name,
                'rc': self._get_random_company_name,
            }
            selected_key = self._supported_keys(org)
            if selected_key not in name_generators:
                raise ValueError(f"Invalid name_generator. Must be one of: {list(name_generators.keys())}")
            return name_generators[selected_key](industry)

        parts = []
        if descriptor:
            parts.append(random.choice(self._vocab['descriptors']))

        if format_type == 'standard':
            parts.extend([
                random.choice(self._vocab['prefixes']),
                random.choice(self._vocab['bases']),
                random.choice(self._vocab['suffixes'])
            ])
        elif format_type == 'short':
            parts.extend([
                random.choice(self._vocab['prefixes']),
                random.choice(self._vocab['suffixes'])
            ])
        elif format_type == 'complex':
            parts.extend([
                random.choice(self._vocab['prefixes']),
                random.choice(self._vocab['bases'])
            ])
            if industry:
                parts.append(random.choice(self._industries[industry]))
            parts.append(random.choice(self._vocab['suffixes']))
        elif format_type == 'modern':
            parts.append(self._create_modern_prefix())
            if random.random() < 0.5:
                parts.append(random.choice(self._vocab['bases']))
            if industry:
                parts.append(random.choice(self._industries[industry]))

        return ' '.join(parts)

    def _generate_acronym_name(self, industry: Optional[str] = None) -> str:
        """Generate an acronym-style company name."""
        words = random.sample(self.prefixes + self.bases, 3)
        if industry:
            words[1] = random.choice(self.industries[industry])

        acronym = ''.join(word[0].upper() for word in words)
        suffix = random.choice(self.suffixes)
        return f"{acronym}{suffix}"

    def _create_modern_prefix(self) -> str:
        """Create a modern prefix by combining parts of two prefixes."""
        word1, word2 = random.sample(self._vocab['prefixes'], 2)
        return word1[:len(word1)//2] + word2[len(word2)//2:]

    def generate_multiple_names(self, count: int, **kwargs) -> List[str]:
        """
        Generate multiple company names.

        Args:
            count: Number of names to generate
            **kwargs: Parameters for generate_name

        Returns:
            List of generated company names

        Raises:
            ValueError: If count is not positive

        """
        if count < 1:
            raise ValueError("Count must be positive")
        return [self.generate_name(**kwargs) for _ in range(count)]

    def customize_vocabulary(self, category: str, words: List[str]) -> None:
        """
        Add words to a vocabulary category.

        Args:
            category: One of 'prefixes', 'bases', 'suffixes', 'descriptors'
            words: Words to add

        Raises:
            ValueError: If invalid category

        """
        if category not in self._vocab:
            raise ValueError(f"Invalid category. Must be one of: {list(self._vocab.keys())}")
        self._vocab[category] = list(set(self._vocab[category] + words))

    def add_industry(self, industry: str, terms: List[str]) -> None:
        """
        Add a new industry with specific terms.

        Args:
            industry: Industry name (letters only)
            terms: Industry-specific terms

        Raises:
            ValueError: If industry name is invalid

        """
        if not re.match(r'^[a-zA-Z]+$', industry):
            raise ValueError("Industry name must contain only letters")
        self._industries[industry] = terms

    def get_available_industries(self) -> List[str]:
        """Return list of available industries."""
        return list(self._industries.keys())

    def _get_random_company_name(self, industry: Optional[str] = None) -> str:
        """
        Generate a random company name from the industries dictionary.

        Args:
            industry: Optional industry to select a company name from (e.g., 'media', 'tech').
                    If None, selects a random name from all industries.

        Returns:
            A randomly selected company name from the specified or all industries.

        Raises:
            ValueError: If the specified industry is not in the industries dictionary.

        """
        if industry:
            if industry not in self._industries:
                raise ValueError(f"Invalid industry. Must be one of: {list(self._industries.keys())}")
            return random.choice(self._industries[industry])

        all_companies = [name for industry_list in self._industries.values() for name in industry_list]
        return random.choice(all_companies)


    def _get_random_prefix_suffix_name(self, industry: Optional[str] = None) -> str:
        """
        Generate a random company name using a prefix and a suffix from the vocabulary.

        Args:
            industry: Optional industry to select an industry-specific suffix (e.g., 'media', 'tech').
                    If None, selects a random suffix from the general vocabulary.

        Returns:
            A company name combining a random prefix and suffix, with spaces between components.

        Raises:
            ValueError: If the specified industry is not in the industries dictionary.

        """
        if industry and industry not in self._industries:
            raise ValueError(f"Invalid industry. Must be one of: {list(self._industries.keys())}")

        prefix = random.choice(self._vocab['prefixes'])
        if industry:
            # Use an industry-specific suffix if available, otherwise fall back to general suffixes
            suffix = random.choice(self._industries[industry]) if random.random() < 0.5 else random.choice(self._vocab['suffixes'])
        else:
            suffix = random.choice(self._vocab['suffixes'])

        return f"{prefix} {suffix}"

    def _get_random_prefix_base_name(self, industry: Optional[str] = None) -> str:
        """
        Generate a random company name using a prefix and a base from the vocabulary.

        Args:
            industry: Optional industry to select an industry-specific base (e.g., 'media', 'tech').
                    If None, selects a random base from the general vocabulary.

        Returns:
            A company name combining a random prefix and base, with spaces between components.

        Raises:
            ValueError: If the specified industry is not in the industries dictionary.

        """
        if industry and industry not in self._industries:
            raise ValueError(f"Invalid industry. Must be one of: {list(self._industries.keys())}")

        prefix = random.choice(self._vocab['prefixes'])
        if industry:
            # Use an industry-specific base if available, otherwise fall back to general bases
            base = random.choice(self._industries[industry]) if random.random() < 0.5 else random.choice(self._vocab['bases'])
        else:
            base = random.choice(self._vocab['bases'])

        return f"{prefix} {base}"

    def _get_random_base_suffix_name(self, industry: Optional[str] = None) -> str:
        """
        Generate a random company name using a base and a suffix from the vocabulary.

        Args:
            industry: Optional industry to select industry-specific base or suffix (e.g., 'media', 'tech').
                    If None, selects random base and suffix from the general vocabulary.

        Returns:
            A company name combining a random base and suffix, with spaces between components.

        Raises:
            ValueError: If the specified industry is not in the industries dictionary.

        """
        if industry and industry not in self._industries:
            raise ValueError(f"Invalid industry. Must be one of: {list(self._industries.keys())}")

        if industry:
            # Use an industry-specific base if available, otherwise fall back to general bases
            base = random.choice(self._industries[industry]) if random.random() < 0.5 else random.choice(self._vocab['bases'])
            # Use an industry-specific suffix if available, otherwise fall back to general suffixes
            suffix = random.choice(self._industries[industry]) if random.random() < 0.5 else random.choice(self._vocab['suffixes'])
        else:
            base = random.choice(self._vocab['bases'])
            suffix = random.choice(self._vocab['suffixes'])

        return f"{base} {suffix}"

if __name__ == "__main__":
    generator = CompanyNameGenerator()
    random_key = generator._supported_keys(None)
    generator.generate_name(org=random_key)
    # print(generator.generate_name(name_generator=random_key))
