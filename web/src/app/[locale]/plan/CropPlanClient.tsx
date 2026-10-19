'use client';

import React, { useState, useEffect, useTransition } from 'react';
import { useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import {
  Header,
  Button,
  Chip,
  SupportedLocale,
} from '@/components/ui';
import { API_BASE } from '@/lib/api';
import {
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  TrendingDown,
  Volume2,
  VolumeX,
  Calendar,
  MapPin,
  AlertTriangle,
  Info,
  CheckCircle2,
  DollarSign,
  Scale,
  Sparkles,
  BookOpen,
  Wheat,
  UserCheck,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { isProductionMode } from '@/lib/appMode';

export interface CropCandidate {
  crop_id: string;
  crop_name_en: string;
  category: string;
  duration_months: number;
  harvest_month: number;
  harvest_month_name: string;
  harvest_price_kg_range: [number, number, number];
  yield_tonnes_acre_range: [number, number, number];
  cost_per_acre_range: [number, number, number];
  profit_per_acre_range: [number, number, number];
  downside_profit_acre: number;
  expected_profit_acre: number;
  upside_profit_acre: number;
  crash_risk_score: number;
  crash_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'SEVERE';
  crowding_factor: number;
  rationale: string;
  agronomic_source: string;
  finance_source: string;
  price_source?: string;
  yield_source?: string;
  cost_source?: string;
  downside_source?: string;
  unrealistic_warning?: string | null;
  recommended_varieties: string[];
}

export interface CropPlanData {
  district: string;
  planting_month: number;
  planting_month_name: string;
  farmer_id: number | null;
  data_sufficiency: string;
  ranked_candidates: CropCandidate[];
  plain_disclaimer: string;
  voice_summary: Record<string, string>;
  sources_and_assumptions: string[];
}

const DISTRICTS = ['Guntur', 'Annamayya', 'Kurnool', 'Krishna'];

const MONTHS = [
  { id: 1, name: 'January' },
  { id: 2, name: 'February' },
  { id: 3, name: 'March' },
  { id: 4, name: 'April' },
  { id: 5, name: 'May' },
  { id: 6, name: 'June' },
  { id: 7, name: 'July' },
  { id: 8, name: 'August' },
  { id: 9, name: 'September' },
  { id: 10, name: 'October' },
  { id: 11, name: 'November' },
  { id: 12, name: 'December' },
];

export const CropPlanClient: React.FC = () => {
  const currentLocale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();
  const [, startTransition] = useTransition();

  const [selectedDistrict, setSelectedDistrict] = useState<string>('Guntur');
  const [selectedMonth, setSelectedMonth] = useState<number>(7); // July default
  const [useFarmerDiary, setUseFarmerDiary] = useState<boolean>(false);
  const [planData, setPlanData] = useState<CropPlanData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [isPlayingVoice, setIsPlayingVoice] = useState<boolean>(false);
  const [selectedCandidate, setSelectedCandidate] = useState<string | null>(null);

  const handleSelectLocale = (newLocale: SupportedLocale) => {
    startTransition(() => {
      const segments = pathname.split('/');
      segments[1] = newLocale;
      router.push(segments.join('/'));
    });
  };

  const fetchPlan = async () => {
    setLoading(true);
    try {
      const farmerParam = useFarmerDiary ? '&farmer_id=1' : '';
      const res = await fetch(
        `${API_BASE}/crop-plan?district=${encodeURIComponent(
          selectedDistrict
        )}&month=${selectedMonth}${farmerParam}`
      );
      if (res.ok) {
        const data = await res.json();
        setPlanData(data);
        if (data.ranked_candidates?.length > 0) {
          setSelectedCandidate(data.ranked_candidates[0].crop_id);
        }
      } else {
        throw new Error('API returned ' + res.status);
      }
    } catch {
      if (isProductionMode) {
        setPlanData(null);
        setSelectedCandidate(null);
        setLoading(false);
        return;
      }
      // Fallback mock data matching the real engine logic for preview and offline dev
      const mockData: CropPlanData = {
        district: selectedDistrict,
        planting_month: selectedMonth,
        planting_month_name: MONTHS[selectedMonth - 1].name,
        farmer_id: useFarmerDiary ? 1 : null,
        data_sufficiency: useFarmerDiary ? 'blended_farmer_diary' : 'regional_norms',
        plain_disclaimer:
          'Guidance only; check with your local agriculture officer or KVK before finalizing seed purchases.',
        sources_and_assumptions: [
          'ANGRAU Agro-Climatic Zone Recommendations & ICAR Krishi Vigyan Kendra Contingency Plans',
          "State Level Bankers' Committee (SLBC) Andhra Pradesh - Scale of Finance 2024-2026",
          'Directorate of Economics & Statistics AP - District Area & Yield Statistics (GODL License)',
          'Historical Agmarknet Modal Mandi Prices 2024-2026',
        ],
        voice_summary: {
          en: `GrowCircle crop advice for ${selectedDistrict} planting in ${
            MONTHS[selectedMonth - 1].name
          }: Banana leads expected profit at Rs. 560,250 per acre. Onion provides a fast 4-month rotation but faces historical glut crash risk (-Rs. 25,500 downside). Green Chilli has elevated price crash risk. Guidance only; consult your local KVK or Agriculture Officer.`,
          te: `గ్రోసర్కిల్ పంట ప్రణాళిక (${selectedDistrict}, ${
            MONTHS[selectedMonth - 1].name
          }): అరటి ఎకరానికి అంచనా లాభం రూ. 560,250 తో ఉంది. ఉల్లి 4 నెలల పంట అయినా మార్కెట్ పతనం నష్ట ప్రమాదం (రూ. -25,500) ఉంది. హెచ్చరిక: మిరప సాగులో ధర పతనం ప్రమాదం ఎక్కువ. మార్గదర్శకత్వం మాత్రమే; స్థానిక కేవీకే లేదా వ్యవసాయ అధికారిని సంప్రదించండి.`,
          hi: `ग्रोसर्कल फसल सलाह (${selectedDistrict}, ${
            MONTHS[selectedMonth - 1].name
          }): केला प्रति एकड़ रु 560,250 अपेक्षित लाभ के साथ पहले स्थान पर है। प्याज में मंडी आवक अधिक होने पर नुकसान (-25,500) का जोखिम है। केवल मार्गदर्शन; अपने स्थानीय केवीके से सलाह लें।`,
          gu: `ગ્રોસર્કલ પાક માર્ગદર્શન (${selectedDistrict}, ${
            MONTHS[selectedMonth - 1].name
          }): કેળા પ્રતિ એકર રૂ 560,250 અંદાજિત નફા સાથે મોખરે છે. ડુંગળીમાં ભારે આવક વખતે ભાવ તૂટવાનું જોખમ છે. માત્ર માર્ગદર્શન; કૃષિ વિજ્ઞાન કેન્દ્રની સલાહ લો.`,
        },
        ranked_candidates: [
          {
            crop_id: 'banana',
            crop_name_en: 'Banana',
            category: 'Fruit / Perennial',
            duration_months: 11,
            harvest_month: ((selectedMonth + 10) % 12) + 1,
            harvest_month_name: MONTHS[((selectedMonth + 10) % 12)].name,
            harvest_price_kg_range: [18.2, 28.5, 42.0],
            yield_tonnes_acre_range: [18.0, 24.5, 30.0],
            cost_per_acre_range: [110000, 138000, 165000],
            profit_per_acre_range: [217600, 560250, 1095000],
            downside_profit_acre: 217600,
            expected_profit_acre: 560250,
            upside_profit_acre: 1095000,
            crash_risk_score: 18,
            crash_risk_level: 'LOW',
            crowding_factor: 0.95,
            rationale:
              'Stable perennial cash crop with steady year-round urban institutional and export demand. High resilience against local price crashes.',
            agronomic_source: 'ANGRAU Horticulture Guide & KVK Banavasi',
            finance_source: 'SLBC AP Scale of Finance 2024-26',
            price_source: 'Agmarknet modal mandi prices 2024-2026',
            yield_source: 'DES AP District Area & Yield Statistics (GODL licensed)',
            cost_source: 'SLBC AP Scale of Finance 2024-26',
            downside_source: 'Agmarknet 10th percentile harvest price',
            unrealistic_warning: 'High Projection Alert: Assumes premium grade pricing and zero pest or weather damage. Actual field returns are typically 20–35% lower.',
            recommended_varieties: ['Grand Naine (G9)', 'Robusta', 'Amruthapani'],
          },
          {
            crop_id: 'onion',
            crop_name_en: 'Onion',
            category: 'Bulb / Vegetable',
            duration_months: 4,
            harvest_month: ((selectedMonth + 3) % 12) + 1,
            harvest_month_name: MONTHS[((selectedMonth + 3) % 12)].name,
            harvest_price_kg_range: [5.0, 26.0, 48.0],
            yield_tonnes_acre_range: [6.5, 14.5, 18.0],
            cost_per_acre_range: [45000, 56000, 70000],
            profit_per_acre_range: [-25500, 321000, 794000],
            downside_profit_acre: -25500,
            expected_profit_acre: 321000,
            upside_profit_acre: 794000,
            crash_risk_score: 55,
            crash_risk_level: 'HIGH',
            crowding_factor: 1.25,
            rationale:
              'Severe price-crash history: peak harvest synchronization in Kurnool and Maharashtra mandis has historically crashed prices to ₹5/kg, causing net losses.',
            agronomic_source: 'ANGRAU Horticultural Research Station (Lam)',
            finance_source: 'SLBC AP Scale of Finance 2024-26',
            price_source: 'Agmarknet modal mandi prices 2024-2026',
            yield_source: 'DES AP District Area & Yield Statistics (GODL licensed)',
            cost_source: 'SLBC AP Scale of Finance 2024-26',
            downside_source: 'Agmarknet historical distress crash price (₹5.0/kg during market glut)',
            recommended_varieties: ['Bhima Super', 'Agrifound Dark Red', 'Arka Kalyan'],
          },
          {
            crop_id: 'chilli',
            crop_name_en: 'Green Chilli',
            category: 'Spices / Vegetable',
            duration_months: 5,
            harvest_month: ((selectedMonth + 4) % 12) + 1,
            harvest_month_name: MONTHS[((selectedMonth + 4) % 12)].name,
            harvest_price_kg_range: [18.0, 38.0, 75.0],
            yield_tonnes_acre_range: [5.5, 9.5, 13.0],
            cost_per_acre_range: [68000, 85000, 105000],
            profit_per_acre_range: [-17000, 276000, 870000],
            downside_profit_acre: -17000,
            expected_profit_acre: 276000,
            upside_profit_acre: 870000,
            crash_risk_score: 68,
            crash_risk_level: 'HIGH',
            crowding_factor: 1.32,
            rationale:
              'Cobweb alert: High district planting share (>18%) combined with high planting-time prices risks a severe harvest supply glut with negative downside returns.',
            agronomic_source: 'ANGRAU Spices Division Guntur & KVK Wyra',
            finance_source: 'SLBC AP Scale of Finance 2024-26',
            price_source: 'Agmarknet modal mandi prices 2024-2026',
            yield_source: 'DES AP District Area & Yield Statistics (GODL licensed)',
            cost_source: 'SLBC AP Scale of Finance 2024-26',
            downside_source: 'Agmarknet historical distress crash price (₹18.0/kg during supply glut)',
            recommended_varieties: ['LCA 334', 'Teja', 'Armoor', 'Byadagi hybrid'],
          },
          {
            crop_id: 'tomato',
            crop_name_en: 'Tomato',
            category: 'Vegetable / Solanaceous',
            duration_months: 3,
            harvest_month: ((selectedMonth + 2) % 12) + 1,
            harvest_month_name: MONTHS[((selectedMonth + 2) % 12)].name,
            harvest_price_kg_range: [3.5, 18.0, 44.0],
            yield_tonnes_acre_range: [11.0, 16.0, 22.0],
            cost_per_acre_range: [48000, 58000, 72000],
            profit_per_acre_range: [-29500, 230000, 896000],
            downside_profit_acre: -29500,
            expected_profit_acre: 230000,
            upside_profit_acre: 896000,
            crash_risk_score: 72,
            crash_risk_level: 'HIGH',
            crowding_factor: 1.28,
            rationale:
              'Highly perishable vegetable with documented price collapses to ₹3.5/kg in Rayalaseema mandis, resulting in net negative downside.',
            agronomic_source: 'Dr. YSR Horticultural University (Venkataramannagudem)',
            finance_source: 'SLBC AP Scale of Finance 2024-26',
            price_source: 'Agmarknet modal mandi prices 2024-2026',
            yield_source: 'DES AP District Area & Yield Statistics (GODL licensed)',
            cost_source: 'SLBC AP Scale of Finance 2024-26',
            downside_source: 'Agmarknet historical distress crash price (₹3.5/kg during peak glut)',
            recommended_varieties: ['Arka Rakshak', 'US 440', 'Saaho 3251'],
          },
          {
            crop_id: 'maize',
            crop_name_en: 'Maize',
            category: 'Cereal / Fodder',
            duration_months: 4,
            harvest_month: ((selectedMonth + 3) % 12) + 1,
            harvest_month_name: MONTHS[((selectedMonth + 3) % 12)].name,
            harvest_price_kg_range: [18.0, 22.0, 26.5],
            yield_tonnes_acre_range: [2.8, 3.8, 4.6],
            cost_per_acre_range: [28000, 35000, 42000],
            profit_per_acre_range: [8400, 48600, 79900],
            downside_profit_acre: 8400,
            expected_profit_acre: 48600,
            upside_profit_acre: 79900,
            crash_risk_score: 12,
            crash_risk_level: 'LOW',
            crowding_factor: 0.88,
            rationale:
              'Very low crash risk supported by feed industry demand and MSP safety net, though maximum upside profit is modest compared to horticulture.',
            agronomic_source: 'ANGRAU Regional Agricultural Research Station (Lam)',
            finance_source: 'SLBC AP Scale of Finance 2024-26',
            price_source: 'Agmarknet modal mandi prices 2024-2026',
            yield_source: 'DES AP District Area & Yield Statistics (GODL licensed)',
            cost_source: 'SLBC AP Scale of Finance 2024-26',
            downside_source: 'Agmarknet 10th percentile harvest price',
            recommended_varieties: ['DHM 117', 'Kargil 900M', 'Pioneer 30V92'],
          },
        ],
      };
      setPlanData(mockData);
      setSelectedCandidate(mockData.ranked_candidates[0].crop_id);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlan();
  }, [selectedDistrict, selectedMonth, useFarmerDiary]);

  const toggleVoiceAdvisory = () => {
    if (!planData) return;
    if (isPlayingVoice) {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      setIsPlayingVoice(false);
      return;
    }

    const textToSpeak =
      planData.voice_summary[currentLocale] ||
      planData.voice_summary['en'] ||
      '';

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      const voiceLangMap: Partial<Record<SupportedLocale, string>> = {
        en: 'en-IN',
        te: 'te-IN',
        hi: 'hi-IN',
        gu: 'gu-IN',
        bn: 'bn-IN',
        mr: 'mr-IN',
        ta: 'ta-IN',
        kn: 'kn-IN',
        ml: 'ml-IN',
        pa: 'pa-IN',
        ur: 'ur-IN',
      };
      utterance.lang = voiceLangMap[currentLocale] || 'en-IN';
      utterance.rate = 0.95;
      utterance.onend = () => setIsPlayingVoice(false);
      utterance.onerror = () => setIsPlayingVoice(false);
      setIsPlayingVoice(true);
      window.speechSynthesis.speak(utterance);
    } else {
      alert(textToSpeak);
    }
  };

  const getRiskBadge = (level: string, score: number) => {
    switch (level) {
      case 'LOW':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-green-100 text-green-800 border border-green-300">
            <ShieldCheck className="w-3.5 h-3.5 text-green-700" />
            Low Crash Risk ({score}/100)
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-yellow-100 text-yellow-800 border border-yellow-300">
            <AlertTriangle className="w-3.5 h-3.5 text-yellow-700" />
            Moderate Risk ({score}/100)
          </span>
        );
      case 'HIGH':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-orange-100 text-orange-800 border border-orange-300">
            <AlertTriangle className="w-3.5 h-3.5 text-orange-700" />
            High Crash Risk ({score}/100)
          </span>
        );
      case 'SEVERE':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-red-100 text-red-800 border border-red-300">
            <ShieldAlert className="w-3.5 h-3.5 text-red-700" />
            Severe Crash Warning ({score}/100)
          </span>
        );
    }
  };

  const formatCurrency = (val: number) => {
    return `₹${Math.round(val).toLocaleString('en-IN')}`;
  };

  return (
    <div className="min-h-screen bg-sand text-ink flex flex-col font-sans">
      <Header
        currentLocale={currentLocale}
        onSelectLocale={handleSelectLocale}
        activeNav="plan"
      />

      <RoleGuard
        allowedRoles={['farmer', 'admin']}
        fallbackTitle="Crop Planning Access Restricted"
        fallbackMessage="Crop planning, regional agricultural guidance, and price-crash risk estimates are available to registered farmers and agronomists. Please sign in with your farmer phone number."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Hero Section */}
        <div className="bg-gradient-to-br from-deep-leaf via-[#18552e] to-[#0e3b1e] rounded-3xl p-6 sm:p-10 text-white shadow-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 rounded-full bg-harvest-gold/15 blur-3xl pointer-events-none" />
          <div className="relative z-10 max-w-3xl space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur border border-white/20 text-xs font-semibold text-harvest-gold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" /> Agricultural Guidance &amp; Crop Planning
            </div>
            <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight font-heading leading-tight">
              Crop Planning &amp; Downside Risk Guidance
            </h1>
            <p className="text-white/85 text-base sm:text-lg leading-relaxed">
              Plan your planting month with probabilistic harvest price analogs and supply-glut
              risk forecasting. We protect you from price crashes caused by over-planting by
              showing realistic ranges—never single numbers.
            </p>

            {/* Mandatory Disclaimer Badge */}
            <div className="flex items-start gap-3 bg-amber-500/20 border border-amber-300/40 rounded-2xl p-4 text-amber-100 text-sm">
              <Info className="w-5 h-5 flex-shrink-0 text-harvest-gold mt-0.5" />
              <div>
                <span className="font-bold text-white">Statutory Advisory Note: </span>
                Guidance only; check with your local agriculture officer or Krishi Vigyan Kendra
                (KVK) before finalizing seed purchases.
              </div>
            </div>
          </div>
        </div>

        {/* Control Bar: District, Month, Farmer Diary toggle, Voice Advisor */}
        <div className="bg-white rounded-2xl shadow-sm border border-border p-5 sm:p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
            {/* District Selector */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-deep-leaf" /> District (Andhra Pradesh)
              </label>
              <select
                value={selectedDistrict}
                onChange={(e) => setSelectedDistrict(e.target.value)}
                className="w-full bg-sand/60 border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf"
              >
                {DISTRICTS.map((d) => (
                  <option key={d} value={d}>
                    {d} District
                  </option>
                ))}
              </select>
            </div>

            {/* Planting Month */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-deep-leaf" /> Planting Month
              </label>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(Number(e.target.value))}
                className="w-full bg-sand/60 border border-border rounded-xl px-3.5 py-2.5 text-sm font-semibold text-ink focus:outline-none focus:ring-2 focus:ring-deep-leaf"
              >
                {MONTHS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} (Month {m.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Farmer Diary Blending Toggle */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-deep-leaf" /> Farm Diary Personalization
              </label>
              <button
                type="button"
                onClick={() => setUseFarmerDiary(!useFarmerDiary)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl border text-sm font-semibold transition-all ${
                  useFarmerDiary
                    ? 'bg-deep-leaf/10 border-deep-leaf text-deep-leaf shadow-sm'
                    : 'bg-sand/60 border-border text-muted hover:text-ink'
                }`}
              >
                <span>{useFarmerDiary ? 'Blended Diary Active' : 'Use Regional Norms'}</span>
                <span
                  className={`w-4 h-4 rounded-full flex items-center justify-center text-xs font-bold ${
                    useFarmerDiary ? 'bg-deep-leaf text-white' : 'bg-gray-300 text-white'
                  }`}
                >
                  {useFarmerDiary ? <CheckCircle2 className="w-3.5 h-3.5" /> : null}
                </span>
              </button>
            </div>

            {/* Spoken Voice Advisory Button */}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-muted uppercase tracking-wider flex items-center gap-1.5">
                <Volume2 className="w-3.5 h-3.5 text-deep-leaf" /> Audio Guidance (&lt; 45s)
              </label>
              <Button
                variant={isPlayingVoice ? 'danger' : 'primary'}
                onClick={toggleVoiceAdvisory}
                className="w-full flex items-center justify-center gap-2"
              >
                {isPlayingVoice ? (
                  <>
                    <VolumeX className="w-4 h-4 animate-pulse" /> Stop Voice Audio
                  </>
                ) : (
                  <>
                    <Volume2 className="w-4 h-4" /> Listen ({currentLocale.toUpperCase()})
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Spoken Voice Transcription preview */}
          {planData && (
            <div className="p-3.5 rounded-xl bg-harvest-gold/10 border border-harvest-gold/30 text-xs sm:text-sm text-ink/90 flex items-start gap-2.5">
              <Volume2 className="w-4 h-4 text-amber flex-shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-ink">Spoken Advisory ({currentLocale.toUpperCase()}): </span>
                {planData.voice_summary[currentLocale] || planData.voice_summary['en']}
              </div>
            </div>
          )}
        </div>

        {/* Sufficiency Mode Badge */}
        {planData && (
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm text-muted px-1">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-ink">Data Foundation:</span>
              <span className="px-2.5 py-0.5 rounded-md bg-white border border-border font-medium text-ink">
                {planData.data_sufficiency === 'blended_farmer_diary'
                  ? '50% Farmer Personal Ledger + 50% SLBC 2024-26 Scale of Finance'
                  : 'SLBC AP Scale of Finance + DES AP Area Statistics (GODL Licensed)'}
              </span>
            </div>
            <div className="text-xs italic">
              All candidates verified for agronomic suitability by ANGRAU / KVK.
            </div>
          </div>
        )}

        {/* Candidate Ranking List */}
        {loading ? (
          <div className="p-16 text-center text-muted animate-pulse">
            Loading agro-climatic candidate projections and crash risk models...
          </div>
        ) : !planData || planData.ranked_candidates.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-2xl border border-border">
            No verified crops suitable for {selectedDistrict} in {MONTHS[selectedMonth - 1].name}.
          </div>
        ) : (
          <div className="space-y-6">
            <h2 className="text-xl sm:text-2xl font-bold font-heading text-ink flex items-center gap-2">
              <Wheat className="w-6 h-6 text-deep-leaf" /> Recommended Crops for {planData.district} (Planting {planData.planting_month_name})
            </h2>

            <div className="grid grid-cols-1 gap-6">
              {planData.ranked_candidates.map((candidate, idx) => {
                const isSelected = selectedCandidate === candidate.crop_id;
                return (
                  <div
                    key={candidate.crop_id}
                    className={`bg-white rounded-3xl border transition-all duration-200 overflow-hidden shadow-sm hover:shadow-md ${
                      isSelected ? 'border-deep-leaf ring-2 ring-deep-leaf/20' : 'border-border'
                    }`}
                  >
                    {/* Header Row */}
                    <div className="p-6 sm:p-7 border-b border-border/70 flex flex-wrap items-center justify-between gap-4 bg-sand/30">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-2xl bg-deep-leaf text-white font-extrabold flex items-center justify-center text-lg shadow-sm">
                          #{idx + 1}
                        </div>
                        <div>
                          <div className="flex items-center gap-2.5">
                            <h3 className="text-xl sm:text-2xl font-extrabold text-ink font-heading">
                              {candidate.crop_name_en}
                            </h3>
                            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-ink/5 text-muted border border-border">
                              {candidate.category}
                            </span>
                          </div>
                          <p className="text-xs text-muted mt-0.5 flex items-center gap-2">
                            <span>Cycle: {candidate.duration_months} Months</span>
                            <span>•</span>
                            <span className="font-semibold text-deep-leaf">
                              Harvest Window: {candidate.harvest_month_name}
                            </span>
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        {getRiskBadge(candidate.crash_risk_level, candidate.crash_risk_score)}
                        <span className="text-xs text-muted font-medium">
                          Crowding: {candidate.crowding_factor}x baseline
                        </span>
                      </div>
                    </div>

                    {/* Financial & Downside Risk Matrix (RANGES ALWAYS) */}
                    <div className="p-6 sm:p-7 space-y-6">
                      {/* Flag Unrealistic Values if present */}
                      {candidate.unrealistic_warning && (
                        <div className="p-4 rounded-2xl bg-amber-500/15 border border-amber-400/40 text-amber-950 flex items-start gap-3 text-xs sm:text-sm">
                          <AlertTriangle className="w-5 h-5 text-amber-700 flex-shrink-0 mt-0.5" />
                          <div>
                            <span className="font-extrabold uppercase tracking-wide text-amber-900 block sm:inline">
                              Flagged Projection Alert:{' '}
                            </span>
                            <span className="font-medium text-amber-900/90">
                              {candidate.unrealistic_warning}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Profit per acre range bar */}
                      <div className="space-y-2 bg-sand/40 p-5 rounded-2xl border border-border/60">
                        <div className="flex items-center justify-between text-xs sm:text-sm">
                          <span className="font-bold text-ink uppercase tracking-wider flex items-center gap-1.5">
                            <DollarSign className="w-4 h-4 text-deep-leaf" /> Expected Net Profit Range / Acre
                          </span>
                          <span className="text-xs text-muted font-medium">
                            Pessimistic (10th) -&gt; Median (50th) -&gt; Optimistic (90th)
                          </span>
                        </div>

                        {/* Three-tier range metrics */}
                        <div className="grid grid-cols-3 gap-3 pt-2 text-center">
                          <div className={`p-3 rounded-xl border shadow-2xs ${candidate.downside_profit_acre < 0 ? 'bg-red-50/70 border-red-200' : 'bg-white border-border/70'}`}>
                            <div className="text-[11px] font-semibold text-red-700 uppercase">Downside Case (10%)</div>
                            <div className={`text-base sm:text-lg font-extrabold ${candidate.downside_profit_acre < 0 ? 'text-red-700' : 'text-ink'}`}>
                              {formatCurrency(candidate.downside_profit_acre)}
                            </div>
                            <div className="text-[10px] text-muted mt-0.5">Glut / Crash Price</div>
                            <div className="text-[9px] text-red-800/80 mt-1 italic border-t border-red-200/50 pt-1">
                              Source: {candidate.downside_source || 'Agmarknet historical 10th percentile'}
                            </div>
                          </div>

                          <div className="bg-deep-leaf/10 p-3 rounded-xl border border-deep-leaf/30 shadow-2xs">
                            <div className="text-[11px] font-bold text-deep-leaf uppercase">Expected (50%)</div>
                            <div className="text-lg sm:text-xl font-extrabold text-deep-leaf">
                              {formatCurrency(candidate.expected_profit_acre)}
                            </div>
                            <div className="text-[10px] text-deep-leaf/80 mt-0.5">Baseline Projection</div>
                            <div className="text-[9px] text-deep-leaf/70 mt-1 italic border-t border-deep-leaf/20 pt-1">
                              Source: DES AP Yield + SLBC Cost Norm
                            </div>
                          </div>

                          <div className="bg-white p-3 rounded-xl border border-border/70 shadow-2xs">
                            <div className="text-[11px] font-semibold text-green-700 uppercase">Upside (90%)</div>
                            <div className="text-base sm:text-lg font-extrabold text-green-700">
                              {formatCurrency(candidate.upside_profit_acre)}
                            </div>
                            <div className="text-[10px] text-muted mt-0.5">Peak Market Price</div>
                            <div className="text-[9px] text-muted mt-1 italic border-t border-border/40 pt-1">
                              Source: Agmarknet 90th percentile
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Supporting Factor Ranges: Price, Yield, Cost with explicit Sources */}
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                        <div className="p-4 rounded-xl bg-sand/30 border border-border/70 space-y-1">
                          <div className="font-semibold text-muted">Harvest Price Range (₹/kg)</div>
                          <div className="text-sm font-bold text-ink">
                            ₹{candidate.harvest_price_kg_range[0]} – ₹{candidate.harvest_price_kg_range[1]} – ₹{candidate.harvest_price_kg_range[2]}
                          </div>
                          <div className="text-[10px] text-muted">Mandi modal distribution</div>
                          <div className="text-[10px] text-deep-leaf font-medium pt-1 border-t border-border/40">
                            Source: {candidate.price_source || 'Agmarknet modal mandi prices 2024-2026'}
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-sand/30 border border-border/70 space-y-1">
                          <div className="font-semibold text-muted">Harvest Yield Range (t/acre)</div>
                          <div className="text-sm font-bold text-ink">
                            {candidate.yield_tonnes_acre_range[0]}t – {candidate.yield_tonnes_acre_range[1]}t – {candidate.yield_tonnes_acre_range[2]}t
                          </div>
                          <div className="text-[10px] text-muted">DES AP district yield norms</div>
                          <div className="text-[10px] text-deep-leaf font-medium pt-1 border-t border-border/40">
                            Source: {candidate.yield_source || 'DES AP District Area & Yield Statistics (GODL licensed)'}
                          </div>
                        </div>

                        <div className="p-4 rounded-xl bg-sand/30 border border-border/70 space-y-1">
                          <div className="font-semibold text-muted">Cultivation Cost Range (₹/acre)</div>
                          <div className="text-sm font-bold text-ink">
                            {formatCurrency(candidate.cost_per_acre_range[0])} – {formatCurrency(candidate.cost_per_acre_range[1])} – {formatCurrency(candidate.cost_per_acre_range[2])}
                          </div>
                          <div className="text-[10px] text-muted">Inputs + labor + machinery</div>
                          <div className="text-[10px] text-deep-leaf font-medium pt-1 border-t border-border/40">
                            Source: {candidate.cost_source || 'SLBC AP Scale of Finance 2024-26'}
                          </div>
                        </div>
                      </div>

                      {/* Rationale and Recommendations */}
                      <div className="space-y-3 pt-1">
                        <p className="text-sm text-ink leading-relaxed">
                          <span className="font-bold">Model Rationale: </span>
                          {candidate.rationale}
                        </p>

                        {candidate.recommended_varieties.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 text-xs">
                            <span className="font-bold text-muted">KVK Recommended Varieties:</span>
                            {candidate.recommended_varieties.map((v) => (
                              <span
                                key={v}
                                className="px-2 py-0.5 rounded-md bg-white border border-border text-ink font-medium"
                              >
                                {v}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Source & Governance Footer */}
                      <div className="pt-3 border-t border-border/60 flex flex-wrap items-center justify-between gap-3 text-[11px] text-muted">
                        <div>
                          <span className="font-semibold">Agronomic Source: </span>
                          {candidate.agronomic_source}
                        </div>
                        <div>
                          <span className="font-semibold">Cost Norm: </span>
                          {candidate.finance_source}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Source Citation & Methodology Panel */}
        {planData && (
          <div className="bg-white rounded-3xl border border-border p-6 sm:p-8 space-y-4 shadow-sm">
            <h3 className="text-lg font-bold font-heading text-ink flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-deep-leaf" /> Verified Sources & Open Government Data Licenses
            </h3>
            <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-muted leading-relaxed">
              {planData.sources_and_assumptions.map((src, idx) => (
                <li key={idx} className="flex items-start gap-2 bg-sand/40 p-3 rounded-xl border border-border/50">
                  <CheckCircle2 className="w-4 h-4 text-deep-leaf flex-shrink-0 mt-0.5" />
                  <span>{src}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </main>
      </RoleGuard>
    </div>
  );
};
