import React from 'react';
import { ArrowRight, Zap, ShieldCheck, Clock, Smartphone } from 'lucide-react';

interface HeroProps {
  onCtaClick: () => void;
  onViewPlans: () => void;
}

const Hero: React.FC<HeroProps> = ({ onCtaClick, onViewPlans }) => {
  return (
    <section className="relative bg-slate-50 pt-28 pb-20 lg:pt-36 lg:pb-28 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-[20%] -right-[10%] w-[70%] h-[70%] rounded-full bg-gradient-to-br from-blue-100/40 to-blue-50/10 blur-3xl" />
        <div className="absolute -bottom-[20%] -left-[10%] w-[60%] h-[60%] rounded-full bg-gradient-to-tr from-blue-100/40 to-transparent blur-3xl" />
      </div>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="lg:grid lg:grid-cols-12 lg:gap-16 items-center">
          
          {/* Text Content */}
          <div className="lg:col-span-6 text-center lg:text-left mb-16 lg:mb-0">
            <div className="inline-flex items-center px-4 py-2 rounded-full bg-blue-100/50 border border-blue-200 text-blue-700 text-sm font-semibold mb-8 shadow-sm animate-fade-in">
              <Zap className="w-4 h-4 mr-2 text-blue-600" fill="currentColor" />
              Inteligência Técnica Instantânea
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 tracking-tight leading-[1.15] mb-6 animate-slide-up">
              A Inteligência que Faltava na{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-blue-400">
                Casa de Máquinas
              </span>
            </h1>

            <p className="text-lg sm:text-xl text-slate-600 mb-10 leading-relaxed animate-slide-up" style={{ animationDelay: '0.1s' }}>
              Resolva falhas de elevadores de qualquer marca ou modelo em minutos.
              De defeitos simples a problemas complexos: a Elevex é a parceira técnica que cabe no seu bolso.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start animate-slide-up" style={{ animationDelay: '0.2s' }}>
              <button
                onClick={onCtaClick}
                className="inline-flex items-center justify-center px-8 py-4 text-base font-bold rounded-2xl text-white bg-blue-600 hover:bg-blue-700 transition-all shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 transform hover:-translate-y-1"
              >
                Começar Agora
                <ArrowRight className="ml-2 h-5 w-5" />
              </button>
              <button
                onClick={onViewPlans}
                className="inline-flex items-center justify-center px-8 py-4 text-base font-semibold rounded-2xl text-slate-700 bg-white border border-slate-200 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 transition-all shadow-sm hover:shadow-md"
              >
                Ver Planos
              </button>
            </div>

            <div className="mt-10 grid grid-cols-3 gap-4 border-t border-slate-200 pt-8 animate-slide-up" style={{ animationDelay: '0.3s' }}>
              <div className="flex flex-col items-center lg:items-start">
                <div className="flex items-center text-slate-700 font-semibold mb-1">
                  <Clock className="w-5 h-5 text-blue-500 mr-2" />
                  <span>Rápido</span>
                </div>
                <span className="text-sm text-slate-500 text-center lg:text-left">Diagnósticos em segundos</span>
              </div>
              <div className="flex flex-col items-center lg:items-start">
                <div className="flex items-center text-slate-700 font-semibold mb-1">
                  <ShieldCheck className="w-5 h-5 text-blue-500 mr-2" />
                  <span>Preciso</span>
                </div>
                <span className="text-sm text-slate-500 text-center lg:text-left">Baseado em manuais reais</span>
              </div>
              <div className="flex flex-col items-center lg:items-start">
                <div className="flex items-center text-slate-700 font-semibold mb-1">
                  <Smartphone className="w-5 h-5 text-blue-400 mr-2" />
                  <span>Prático</span>
                </div>
                <span className="text-sm text-slate-500 text-center lg:text-left">Na palma da sua mão</span>
              </div>
            </div>
          </div>

          {/* Image/Mockup */}
          <div className="lg:col-span-6 relative animate-fade-in" style={{ animationDelay: '0.2s' }}>
            <div className="relative rounded-3xl overflow-hidden shadow-2xl border border-slate-200/50 bg-white aspect-[4/3] lg:aspect-auto lg:h-[600px]">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-800 to-slate-900"></div>
              
              {/* Abstract App Representation */}
              <div className="absolute inset-0 flex flex-col p-6">
                {/* App Header */}
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-500 flex items-center justify-center shadow-lg">
                      <Zap className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <div className="h-4 w-24 bg-slate-700 rounded-md mb-2"></div>
                      <div className="h-3 w-16 bg-slate-600 rounded-md"></div>
                    </div>
                  </div>
                  <div className="w-8 h-8 rounded-full bg-slate-700"></div>
                </div>

                {/* Chat Area */}
                <div className="flex-1 flex flex-col gap-4">
                  <div className="self-end max-w-[80%] bg-blue-600 rounded-2xl rounded-tr-sm p-4 shadow-md">
                    <div className="h-4 w-48 bg-blue-400/50 rounded-md mb-2"></div>
                    <div className="h-4 w-32 bg-blue-400/50 rounded-md"></div>
                  </div>
                  
                  <div className="self-start max-w-[80%] bg-slate-700 rounded-2xl rounded-tl-sm p-4 shadow-md">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center">
                        <Zap className="w-3 h-3 text-white" />
                      </div>
                      <div className="h-3 w-20 bg-slate-500 rounded-md"></div>
                    </div>
                    <div className="h-4 w-56 bg-slate-500/50 rounded-md mb-2"></div>
                    <div className="h-4 w-64 bg-slate-500/50 rounded-md mb-2"></div>
                    <div className="h-4 w-40 bg-slate-500/50 rounded-md"></div>
                    
                    <div className="mt-4 p-3 bg-slate-800 rounded-xl border border-slate-600">
                      <div className="flex items-center gap-2 mb-2">
                        <ShieldCheck className="w-4 h-4 text-blue-400" />
                        <div className="h-3 w-24 bg-slate-500 rounded-md"></div>
                      </div>
                      <div className="h-3 w-full bg-slate-600/50 rounded-md mb-1.5"></div>
                      <div className="h-3 w-3/4 bg-slate-600/50 rounded-md"></div>
                    </div>
                  </div>
                </div>

                {/* Input Area */}
                <div className="mt-6 h-14 bg-slate-800 rounded-2xl border border-slate-600 flex items-center px-4">
                  <div className="h-4 w-48 bg-slate-600 rounded-md"></div>
                  <div className="ml-auto w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                    <ArrowRight className="w-4 h-4 text-white" />
                  </div>
                </div>
              </div>
            </div>
            
            {/* Floating Badge */}
            <div className="absolute -bottom-6 -left-6 bg-white p-4 rounded-2xl shadow-xl border border-slate-100 flex items-center gap-4 animate-slide-up" style={{ animationDelay: '0.5s' }}>
              <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                <ShieldCheck className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-bold text-slate-900">99.9% de Precisão</p>
                <p className="text-xs text-slate-500">Em diagnósticos técnicos</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </section>
  );
};

export default Hero;