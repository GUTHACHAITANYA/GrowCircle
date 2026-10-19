'use client';

import React, { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import {
  Header,
  Button,
  Card,
  Chip,
  SupportedLocale,
} from '@/components/ui';
import {
  TrendingUp,
  Download,
  Calendar,
  Layers,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  PlusCircle,
  X,
  Volume2,
  Scale,
  DollarSign,
  FileText,
  PieChart,
  Mic,
  Check,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';
import { isDemoMode, isProductionMode } from '@/lib/appMode';

interface PlotSeason {
  id: number;
  seasonName: string;
  crop: string;
  variety: string;
  areaAcres: number;
  plantingDate: string;
  harvestDate: string;
  expectedYieldKg: number;
  district: string;
}

interface DiaryEntry {
  id: number;
  entryType: 'cost' | 'yield_log' | 'sale_revenue';
  category: string;
  amountInr: number;
  quantityKg: number;
  unitPriceInr: number;
  entryDate: string;
  notes: string;
  readbackConfirmed: boolean;
}

const INITIAL_SEASON: PlotSeason = {
  id: 101,
  seasonName: 'Kharif Banana 2026',
  crop: 'Banana',
  variety: 'Amruthapani (Grade A)',
  areaAcres: 2.5,
  plantingDate: '2026-06-01',
  harvestDate: '2026-10-15',
  expectedYieldKg: 5000,
  district: 'Guntur, Andhra Pradesh',
};

const INITIAL_ENTRIES: DiaryEntry[] = [
  {
    id: 1,
    entryType: 'cost',
    category: 'seeds',
    amountInr: 12500,
    quantityKg: 0,
    unitPriceInr: 0,
    entryDate: '2026-06-02',
    notes: '800 tissue culture saplings from certified nursery',
    readbackConfirmed: true,
  },
  {
    id: 2,
    entryType: 'cost',
    category: 'fertilizer',
    amountInr: 6800,
    quantityKg: 0,
    unitPriceInr: 0,
    entryDate: '2026-06-25',
    notes: 'DAP & organic neem cake base dosage',
    readbackConfirmed: true,
  },
  {
    id: 3,
    entryType: 'cost',
    category: 'labour',
    amountInr: 8500,
    quantityKg: 0,
    unitPriceInr: 0,
    entryDate: '2026-07-15',
    notes: 'Field weeding, earthing up, and drainage trenching',
    readbackConfirmed: true,
  },
  {
    id: 4,
    entryType: 'cost',
    category: 'irrigation',
    amountInr: 3200,
    quantityKg: 0,
    unitPriceInr: 0,
    entryDate: '2026-08-10',
    notes: 'Drip line replacement & pump electricity',
    readbackConfirmed: true,
  },
  {
    id: 5,
    entryType: 'yield_log',
    category: 'harvest',
    amountInr: 0,
    quantityKg: 3800,
    unitPriceInr: 0,
    entryDate: '2026-10-08',
    notes: 'First cut harvest - 380 crates of Grade A bunches',
    readbackConfirmed: true,
  },
  {
    id: 6,
    entryType: 'sale_revenue',
    category: 'sale',
    amountInr: 108300,
    quantityKg: 3800,
    unitPriceInr: 28.5,
    entryDate: '2026-10-10',
    notes: 'Direct institutional supply contract with ANU Hostel',
    readbackConfirmed: true,
  },
];

export function DiaryClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  const todayIso = new Date().toISOString().split('T')[0];
  const [season, setSeason] = useState<PlotSeason>(
    isDemoMode
      ? INITIAL_SEASON
      : {
          id: 1,
          seasonName: '',
          crop: '',
          variety: '',
          areaAcres: 0,
          plantingDate: todayIso,
          harvestDate: '',
          expectedYieldKg: 0,
          district: 'Guntur',
        }
  );
  const [entries, setEntries] = useState<DiaryEntry[]>(isDemoMode ? INITIAL_ENTRIES : []);

  // New Entry Form State
  const [showAddModal, setShowAddModal] = useState(false);
  const [entryType, setEntryType] = useState<'cost' | 'yield_log' | 'sale_revenue'>('cost');
  const [entryCategory, setEntryCategory] = useState('labour');
  const [entryAmount, setEntryAmount] = useState<number>(3500);
  const [entryQty, setEntryQty] = useState<number>(0);
  const [entryUnitPrice, setEntryUnitPrice] = useState<number>(0);
  const [entryDate, setEntryDate] = useState(todayIso);
  const [entryNotes, setEntryNotes] = useState('');

  // Voice Entry & Read-back Confirmation State
  const [showVoiceModal, setShowVoiceModal] = useState(false);
  const [voiceSampleText, setVoiceSampleText] = useState('Spent 5000 on harvesting labour yesterday');
  const [readbackDraft, setReadbackDraft] = useState<{
    entryType: 'cost' | 'yield_log' | 'sale_revenue';
    category: string;
    amountInr: number;
    quantityKg: number;
    unitPriceInr: number;
    date: string;
    notes: string;
    spokenPrompt: string;
  } | null>(null);

  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  // Financial Computations
  const totalCost = entries
    .filter((e) => e.entryType === 'cost')
    .reduce((sum, e) => sum + e.amountInr, 0);

  const totalHarvestedKg = entries
    .filter((e) => e.entryType === 'yield_log')
    .reduce((sum, e) => sum + e.quantityKg, 0);

  const totalRevenue = entries
    .filter((e) => e.entryType === 'sale_revenue')
    .reduce((sum, e) => sum + e.amountInr, 0);

  const totalSoldKg = entries
    .filter((e) => e.entryType === 'sale_revenue')
    .reduce((sum, e) => sum + e.quantityKg, 0);

  const netProfitLoss = totalRevenue - totalCost;
  const profitLossPerAcre = Math.round(netProfitLoss / season.areaAcres);

  // Break-even price
  const effectiveHarvestKg = totalHarvestedKg > 0 ? totalHarvestedKg : season.expectedYieldKg;
  const breakEvenPriceKg =
    effectiveHarvestKg > 0 ? (totalCost / effectiveHarvestKg).toFixed(2) : '0.00';

  // Farmer actual sale price vs Mandi average
  const farmerActualPriceKg = totalSoldKg > 0 ? totalRevenue / totalSoldKg : 0;
  const mandiAveragePriceKg = 24.2; // Modal average in Guntur over same dates
  const pricePremiumInr = (farmerActualPriceKg - mandiAveragePriceKg).toFixed(2);
  const pricePremiumPercent = (
    ((farmerActualPriceKg - mandiAveragePriceKg) / mandiAveragePriceKg) *
    100
  ).toFixed(1);

  // Save regular form entry
  const handleSaveFormEntry = (e: React.FormEvent) => {
    e.preventDefault();
    const newEntry: DiaryEntry = {
      id: Date.now(),
      entryType,
      category: entryType === 'sale_revenue' ? 'sale' : entryType === 'yield_log' ? 'harvest' : entryCategory,
      amountInr: entryType === 'sale_revenue' ? entryQty * entryUnitPrice : entryAmount,
      quantityKg: entryQty,
      unitPriceInr: entryUnitPrice,
      entryDate,
      notes: entryNotes,
      readbackConfirmed: true,
    };
    setEntries([newEntry, ...entries]);
    setShowAddModal(false);
    showToast('Ledger entry recorded! Economics and break-even updated.');
  };

  // Parse voice text and generate read-back confirmation
  const handleSimulateVoice = () => {
    const text = voiceSampleText.toLowerCase();
    const numbers = text.match(/\d+(\.\d+)?/g);
    const amount = numbers ? parseFloat(numbers[0]) : 5000;

    let cat = 'labour';
    let type: 'cost' | 'yield_log' | 'sale_revenue' = 'cost';

    if (text.includes('harvest') || text.includes('yield')) {
      type = 'yield_log';
      cat = 'harvest';
    } else if (text.includes('sold') || text.includes('sale')) {
      type = 'sale_revenue';
      cat = 'sale';
    } else if (text.includes('fertilizer') || text.includes('dap') || text.includes('urea')) {
      cat = 'fertilizer';
    } else if (text.includes('seed') || text.includes('sapling')) {
      cat = 'seeds';
    } else if (text.includes('diesel') || text.includes('tractor')) {
      cat = 'machinery';
    }

    let readbackPrompt = '';
    if (locale === 'te') {
      readbackPrompt = `ధృవీకరణ: ${todayIso}న ${cat} కోసం ₹${amount.toLocaleString('en-IN')} ఖర్చు నమోదు చేయమంటారా?`;
    } else if (locale === 'hi') {
      readbackPrompt = `पुष्टि करें: ${todayIso} को ${cat} पर ₹${amount.toLocaleString('en-IN')} का खर्च दर्ज करें?`;
    } else if (locale === 'gu') {
      readbackPrompt = `ખાતરી કરો: ${todayIso} ના રોજ ${cat} પાછળ ₹${amount.toLocaleString('en-IN')} નો ખર્ચ નોંધવો છે?`;
    } else {
      readbackPrompt = `Confirming cost entry: ₹${amount.toLocaleString('en-IN')} spent on ${cat} on ${todayIso}. Save this entry?`;
    }

    setReadbackDraft({
      entryType: type,
      category: cat,
      amountInr: amount,
      quantityKg: type === 'yield_log' ? amount : 0,
      unitPriceInr: 0,
      date: todayIso,
      notes: voiceSampleText,
      spokenPrompt: readbackPrompt,
    });
  };

  const handleConfirmVoiceEntry = () => {
    if (!readbackDraft) return;
    const newEntry: DiaryEntry = {
      id: Date.now(),
      entryType: readbackDraft.entryType,
      category: readbackDraft.category,
      amountInr: readbackDraft.amountInr,
      quantityKg: readbackDraft.quantityKg,
      unitPriceInr: readbackDraft.unitPriceInr,
      entryDate: readbackDraft.date,
      notes: readbackDraft.notes,
      readbackConfirmed: true,
    };
    setEntries([newEntry, ...entries]);
    setReadbackDraft(null);
    setShowVoiceModal(false);
    showToast('Voice entry confirmed and saved to ledger!');
  };

  const handleDownloadCsv = () => {
    let csv = `GrowCircle Farm Diary Export\n`;
    csv += `Season,${season.seasonName}\n`;
    csv += `Crop,${season.crop}\n`;
    csv += `Area (Acres),${season.areaAcres}\n`;
    csv += `Total Expenses (INR),${totalCost}\n`;
    csv += `Total Revenue (INR),${totalRevenue}\n`;
    csv += `Net Profit/Loss (INR),${netProfitLoss}\n`;
    csv += `Profit/Loss Per Acre (INR),${profitLossPerAcre}\n`;
    csv += `Break-Even Price (INR/kg),${breakEvenPriceKg}\n`;
    csv += `Mandi Average Price (INR/kg),${mandiAveragePriceKg}\n`;
    csv += `Farmer Realized Price (INR/kg),${farmerActualPriceKg.toFixed(2)}\n\n`;
    csv += `Date,Type,Category,Amount (INR),Quantity (kg),Notes,Confirmed\n`;

    entries.forEach((e) => {
      csv += `${e.entryDate},${e.entryType},${e.category},${e.amountInr},${e.quantityKg},"${e.notes}",YES\n`;
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `growcircle_diary_season_${season.id}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('Farm records exported to CSV successfully!');
  };

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
        activeNav="diary"
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-deep-leaf text-white px-5 py-3 rounded-2xl shadow-xl flex items-center gap-3 animate-slide-up border border-white/20">
          <CheckCircle2 className="w-5 h-5 text-harvest-gold flex-shrink-0" />
          <span className="text-sm font-semibold">{toastMessage}</span>
        </div>
      )}

      <RoleGuard
        allowedRoles={['farmer', 'admin']}
        fallbackTitle="Farm Diary Access Restricted"
        fallbackMessage="This digital farm ledger tracks plot seasons, input costs, and yield economics for verified farmers. Sign in with your farmer phone number to view and record entries."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* SEASON & PLOT HEADER */}
        <div className="bg-white rounded-3xl border border-border p-6 shadow-sm mb-6 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center flex-shrink-0">
              <TrendingUp className="w-7 h-7" />
            </div>
            <div>
              <span className="text-xs font-bold text-deep-leaf uppercase tracking-wider block mb-0.5">
                {t('diary.title')}
              </span>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="font-heading text-2xl font-extrabold text-ink">
                  {season.seasonName}
                </h1>
                <Chip variant="primary" size="sm">
                  {season.areaAcres} Acres Plot
                </Chip>
                <Chip variant="default" size="sm">
                  {season.variety}
                </Chip>
              </div>
              <p className="text-xs text-muted mt-1">
                District: <strong>{season.district}</strong> &bull; Planting: <strong>{season.plantingDate}</strong> &bull; Harvest: <strong>{season.harvestDate}</strong>
              </p>
            </div>
          </div>

          {/* QUICK ACTIONS */}
          <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto">
            <Button
              variant="secondary"
              size="md"
              onClick={handleDownloadCsv}
              leftIcon={<Download className="w-4 h-4 text-deep-leaf" />}
            >
              {t('diary.exportRecords')}
            </Button>
            <Button
              variant="secondary"
              size="md"
              onClick={() => setShowVoiceModal(true)}
              leftIcon={<Mic className="w-4 h-4 text-amber" />}
            >
              {t('diary.voiceEntry')}
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowAddModal(true)}
              leftIcon={<PlusCircle className="w-4 h-4" />}
            >
              {t('diary.addCost')}
            </Button>
          </div>
        </div>

        {/* 4 CORE ECONOMIC METRICS CARDS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* Card 1: Total Cost */}
          <Card className="p-5 bg-white border border-border">
            <span className="text-xs font-bold text-muted uppercase tracking-wider block mb-1">
              Total Cultivation Cost
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-extrabold text-ink font-heading">
                ₹{totalCost.toLocaleString('en-IN')}
              </span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              Seeds, labour, fertilizers, irrigation &amp; transport
            </p>
          </Card>

          {/* Card 2: Total Revenue */}
          <Card className="p-5 bg-white border border-border">
            <span className="text-xs font-bold text-muted uppercase tracking-wider block mb-1">
              Total Sales Revenue
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-extrabold text-deep-leaf font-heading">
                ₹{totalRevenue.toLocaleString('en-IN')}
              </span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              {totalSoldKg.toLocaleString('en-IN')} kg sold at ₹{farmerActualPriceKg.toFixed(1)}/kg average
            </p>
          </Card>

          {/* Card 3: Profit & Loss Per Acre */}
          <Card className="p-5 bg-white border border-border">
            <span className="text-xs font-bold text-muted uppercase tracking-wider block mb-1">
              {t('diary.profitPerAcre')}
            </span>
            <div className="flex items-baseline gap-2">
              <span
                className={`text-2xl sm:text-3xl font-extrabold font-heading ${
                  profitLossPerAcre >= 0 ? 'text-deep-leaf' : 'text-danger'
                }`}
              >
                ₹{profitLossPerAcre.toLocaleString('en-IN')}
              </span>
              <span className="text-xs text-muted font-bold">/ acre</span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              Net Profit: <strong>₹{netProfitLoss.toLocaleString('en-IN')}</strong> across {season.areaAcres} acres
            </p>
          </Card>

          {/* Card 4: Break-Even Price */}
          <Card className="p-5 bg-white border border-border">
            <span className="text-xs font-bold text-muted uppercase tracking-wider block mb-1">
              {t('diary.breakEven')}
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl sm:text-3xl font-extrabold text-amber font-heading">
                ₹{breakEvenPriceKg}
              </span>
              <span className="text-xs text-muted font-bold">/ kg</span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              Minimum price required per kg to cover all expenses
            </p>
          </Card>
        </div>

        {/* SEASON SUMMARY VS MANDI AVERAGE COMPARISON */}
        <div className="bg-white rounded-3xl border border-border p-6 shadow-sm mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border">
            <div>
              <div className="flex items-center gap-2">
                <Scale className="w-5 h-5 text-deep-leaf" />
                <h2 className="font-heading text-lg sm:text-xl font-bold text-ink">
                  {t('diary.seasonSummary')}
                </h2>
              </div>
              <p className="text-xs text-muted mt-0.5">
                Benchmark comparison against daily Agmarknet mandi modal prices for {season.district} during your season.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <div className="bg-deep-leaf/10 text-deep-leaf px-3.5 py-1.5 rounded-xl font-bold text-sm flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>+₹{pricePremiumInr}/kg (+{pricePremiumPercent}%) Premium</span>
              </div>
            </div>
          </div>

          <div className="py-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div className="bg-cream rounded-2xl p-4 border border-border">
              <span className="text-muted block mb-0.5">Mandi Average (Same Dates)</span>
              <span className="text-2xl font-extrabold text-ink font-heading">
                ₹{mandiAveragePriceKg}/kg
              </span>
              <p className="text-[11px] text-muted mt-1">
                Average Guntur wholesale arrival modal rate
              </p>
            </div>

            <div className="bg-cream rounded-2xl p-4 border border-border">
              <span className="text-muted block mb-0.5">Your Realized Sale Price</span>
              <span className="text-2xl font-extrabold text-deep-leaf font-heading">
                ₹{farmerActualPriceKg.toFixed(2)}/kg
              </span>
              <p className="text-[11px] text-muted mt-1">
                Direct sale to institutional buyer on GrowCircle
              </p>
            </div>

            <div className="bg-deep-leaf/5 rounded-2xl p-4 border border-deep-leaf/20 flex flex-col justify-between">
              <div>
                <span className="text-deep-leaf font-bold block mb-0.5">Direct Selling Dividend</span>
                <p className="text-ink text-xs leading-relaxed">
                  By cutting out multiple intermediary commissions, you gained an extra <strong>₹{(parseFloat(pricePremiumInr) * totalSoldKg).toLocaleString('en-IN')}</strong> in take-home income on this {totalSoldKg.toLocaleString('en-IN')} kg harvest.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* LEDGER ENTRIES TABLE */}
        <div className="bg-white rounded-3xl border border-border p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div>
              <h3 className="font-heading text-lg font-bold text-ink">
                Cultivation Ledger &amp; Voice Entries
              </h3>
              <p className="text-xs text-muted">
                Complete record of input expenses, harvest cuts, and direct produce sales.
              </p>
            </div>
            <span className="text-xs text-muted">
              {entries.length} Ledger Records
            </span>
          </div>

          <div className="space-y-3">
            {entries.map((entry) => (
              <div
                key={entry.id}
                className="bg-cream/50 rounded-2xl p-4 border border-border flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-deep-leaf/30 transition-colors"
              >
                <div className="flex items-start sm:items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-xs flex-shrink-0 ${
                      entry.entryType === 'cost'
                        ? 'bg-danger/10 text-danger'
                        : entry.entryType === 'yield_log'
                        ? 'bg-harvest-gold/20 text-ink'
                        : 'bg-deep-leaf/10 text-deep-leaf'
                    }`}
                  >
                    {entry.entryType === 'cost' ? 'EXP' : entry.entryType === 'yield_log' ? 'CUT' : 'SALE'}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="font-heading text-sm font-bold text-ink capitalize">
                        {entry.category}
                      </h4>
                      <Chip variant="default" size="sm">
                        {entry.entryDate}
                      </Chip>
                    </div>
                    <p className="text-xs text-muted mt-0.5">{entry.notes}</p>
                  </div>
                </div>

                <div className="text-right sm:text-right">
                  {entry.entryType === 'cost' && (
                    <span className="text-base font-extrabold text-danger font-heading">
                      -₹{entry.amountInr.toLocaleString('en-IN')}
                    </span>
                  )}
                  {entry.entryType === 'yield_log' && (
                    <span className="text-base font-extrabold text-ink font-heading">
                      +{entry.quantityKg.toLocaleString('en-IN')} kg
                    </span>
                  )}
                  {entry.entryType === 'sale_revenue' && (
                    <div>
                      <span className="text-base font-extrabold text-deep-leaf font-heading block">
                        +₹{entry.amountInr.toLocaleString('en-IN')}
                      </span>
                      <span className="text-[11px] text-muted">
                        {entry.quantityKg} kg @ ₹{entry.unitPriceInr}/kg
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
      </RoleGuard>

      {/* MODAL: ADD MANUAL ENTRY */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in my-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading text-xl font-bold text-ink">
                Add Farm Ledger Entry
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveFormEntry} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-ink mb-1">Entry Type</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setEntryType('cost')}
                    className={`p-2 rounded-xl border font-bold ${
                      entryType === 'cost'
                        ? 'bg-deep-leaf text-white border-deep-leaf'
                        : 'bg-white border-border text-ink'
                    }`}
                  >
                    Expense
                  </button>
                  <button
                    type="button"
                    onClick={() => setEntryType('yield_log')}
                    className={`p-2 rounded-xl border font-bold ${
                      entryType === 'yield_log'
                        ? 'bg-deep-leaf text-white border-deep-leaf'
                        : 'bg-white border-border text-ink'
                    }`}
                  >
                    Harvest Cut
                  </button>
                  <button
                    type="button"
                    onClick={() => setEntryType('sale_revenue')}
                    className={`p-2 rounded-xl border font-bold ${
                      entryType === 'sale_revenue'
                        ? 'bg-deep-leaf text-white border-deep-leaf'
                        : 'bg-white border-border text-ink'
                    }`}
                  >
                    Sale Revenue
                  </button>
                </div>
              </div>

              {entryType === 'cost' && (
                <div>
                  <label className="block font-bold text-ink mb-1">Cost Category</label>
                  <select
                    value={entryCategory}
                    onChange={(e) => setEntryCategory(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-border font-bold bg-white text-ink"
                  >
                    <option value="seeds">Seeds / Saplings</option>
                    <option value="fertilizer">Fertilizers &amp; Manure</option>
                    <option value="labour">Labour &amp; Weeding</option>
                    <option value="irrigation">Irrigation &amp; Power</option>
                    <option value="machinery">Tractor &amp; Machinery</option>
                    <option value="transport">Transport &amp; Freight</option>
                    <option value="other">Miscellaneous</option>
                  </select>
                </div>
              )}

              {entryType === 'cost' && (
                <div>
                  <label className="block font-bold text-ink mb-1">Amount (₹)</label>
                  <input
                    type="number"
                    value={entryAmount}
                    onChange={(e) => setEntryAmount(parseFloat(e.target.value) || 0)}
                    className="w-full p-2.5 rounded-xl border border-border font-bold text-sm text-ink"
                  />
                </div>
              )}

              {entryType === 'yield_log' && (
                <div>
                  <label className="block font-bold text-ink mb-1">Harvested Quantity (kg)</label>
                  <input
                    type="number"
                    value={entryQty}
                    onChange={(e) => setEntryQty(parseFloat(e.target.value) || 0)}
                    className="w-full p-2.5 rounded-xl border border-border font-bold text-sm text-ink"
                  />
                </div>
              )}

              {entryType === 'sale_revenue' && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-ink mb-1">Sold Quantity (kg)</label>
                    <input
                      type="number"
                      value={entryQty}
                      onChange={(e) => setEntryQty(parseFloat(e.target.value) || 0)}
                      className="w-full p-2.5 rounded-xl border border-border font-bold text-sm text-ink"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-ink mb-1">Price per kg (₹)</label>
                    <input
                      type="number"
                      value={entryUnitPrice}
                      onChange={(e) => setEntryUnitPrice(parseFloat(e.target.value) || 0)}
                      className="w-full p-2.5 rounded-xl border border-border font-bold text-sm text-ink"
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block font-bold text-ink mb-1">Date</label>
                <input
                  type="date"
                  value={entryDate}
                  onChange={(e) => setEntryDate(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-border font-bold text-ink"
                />
              </div>

              <div>
                <label className="block font-bold text-ink mb-1">Notes</label>
                <input
                  type="text"
                  placeholder="e.g. 5 worker days for weeding"
                  value={entryNotes}
                  onChange={(e) => setEntryNotes(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-border text-ink"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="flex-1"
                  onClick={() => setShowAddModal(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" className="flex-1">
                  Save Entry
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL: VOICE ENTRY WITH READ-BACK CONFIRMATION */}
      {showVoiceModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-border animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Mic className="w-6 h-6 text-deep-leaf" />
                <h3 className="font-heading text-xl font-bold text-ink">
                  {t('diary.readbackTitle')}
                </h3>
              </div>
              <button
                onClick={() => {
                  setShowVoiceModal(false);
                  setReadbackDraft(null);
                }}
                className="p-1 rounded-full text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-muted mb-4 leading-relaxed">
              {t('diary.readbackPrompt')}
            </p>

            <div className="mb-4">
              <label className="block text-xs font-bold text-ink mb-1.5">
                Spoken Voice Phrase:
              </label>
              <textarea
                value={voiceSampleText}
                onChange={(e) => setVoiceSampleText(e.target.value)}
                rows={2}
                className="w-full p-2.5 rounded-xl border border-border text-xs text-ink focus:ring-2 focus:ring-deep-leaf"
              />
            </div>

            {!readbackDraft ? (
              <Button
                variant="primary"
                className="w-full"
                onClick={handleSimulateVoice}
                leftIcon={<Volume2 className="w-4 h-4" />}
              >
                Transcribe &amp; Generate Read-Back
              </Button>
            ) : (
              <div className="space-y-4">
                {/* READ-BACK CONFIRMATION BOX */}
                <div className="bg-deep-leaf/5 border-2 border-deep-leaf/30 rounded-2xl p-4 text-xs">
                  <div className="flex items-center gap-2 text-deep-leaf font-bold mb-2">
                    <Volume2 className="w-4 h-4" />
                    <span>Spoken Read-Back Confirmation:</span>
                  </div>
                  <p className="text-ink font-semibold italic text-sm leading-relaxed mb-3">
                    &quot;{readbackDraft.spokenPrompt}&quot;
                  </p>
                  <div className="bg-white p-2.5 rounded-xl border border-border text-xs flex justify-between">
                    <span>Parsed Category: <strong>{readbackDraft.category}</strong></span>
                    <span>Amount: <strong>₹{readbackDraft.amountInr}</strong></span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Button
                    variant="secondary"
                    className="flex-1"
                    onClick={() => setReadbackDraft(null)}
                  >
                    Re-Record
                  </Button>
                  <Button
                    variant="primary"
                    className="flex-1"
                    onClick={handleConfirmVoiceEntry}
                    leftIcon={<Check className="w-4 h-4" />}
                  >
                    {t('diary.confirmSave')}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
