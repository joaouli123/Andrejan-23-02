import React from 'react';
import { Database, Zap, Search, ShieldCheck, Wrench, Layers, Cpu, ArrowRight } from 'lucide-react';

const Features: React.FC = () => {
  return (
    <div id="features" className="py-24 bg-white relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-full pointer-events-none">
        <div className="absolute top-20 left-10 w-72 h-72 bg-blue-50 rounded-full blur-3xl opacity-50"></div>
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-cyan-50 rounded-full blur-3xl opacity-50"></div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        
        {/* Main Value Prop */}
        <div className="text-center max-w-3xl mx-auto mb-20">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-600 text-xs font-bold tracking-wide uppercase mb-4">
            <Cpu className="w-3 h-3 mr-2" />
            Tecnologia Exclusiva
          </div>
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl lg:text-5xl tracking-tight mb-6">
            Transforme Defeitos Complexos em{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">
              Soluções Simples
            </span>
          </h2>
          <p className="text-lg sm:text-xl text-slate-600 leading-relaxed">
            A Elevex não é apenas um app; é a ferramenta definitiva para o setor de transporte vertical. Reunimos em um só lugar um banco de dados construído sobre mais de 20 anos de experiência de campo.
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-12">
          <div className="bg-white rounded-3xl p-8 border border-slate-100 shadow-lg shadow-slate-200/40 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group">
            <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Database className="w-7 h-7 text-blue-600" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-3">Cruza Dados</h3>
            <p className="text-slate-600 leading-relaxed">
              Nossa tecnologia cruza dados de diferentes marcas, modelos e nacionalidades para entregar o suporte exato que você precisa.
            </p>
          </div>

          <div className="bg-white rounded-3xl p-8 border border-slate-100 shadow-lg shadow-slate-200/40 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group">
             <div className="w-14 h-14 bg-amber-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Search className="w-7 h-7 text-amber-600" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-3">Diagnóstico Preciso</h3>
            <p className="text-slate-600 leading-relaxed">
              Identifique códigos de falha obscuros rapidamente. A Elevex decifra manuais complexos em segundos.
            </p>
          </div>

          <div className="bg-white rounded-3xl p-8 border border-slate-100 shadow-lg shadow-slate-200/40 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group">
             <div className="w-14 h-14 bg-green-50 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
              <Wrench className="w-7 h-7 text-green-600" />
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-3">Guia de Reparo</h3>
            <p className="text-slate-600 leading-relaxed">
              Não apenas dizemos o problema, guiamos o reparo. Passos lógicos para resolver falhas de alta complexidade.
            </p>
          </div>
        </div>

        {/* Problem / Solution Section */}
        <div className="mt-32 lg:grid lg:grid-cols-2 lg:gap-0 items-center bg-slate-900 rounded-[2.5rem] overflow-hidden shadow-2xl border border-slate-800">
          <div className="p-10 lg:p-16 relative z-10">
            <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-blue-900/20 to-transparent pointer-events-none"></div>
            
            <h3 className="text-3xl font-bold text-white mb-8 relative z-10">Por Que Escolher a Elevex?</h3>
            <blockquote className="text-slate-300 italic mb-12 border-l-4 border-blue-500 pl-6 relative z-10 text-lg">
              "A Elevex nasceu da união entre técnicos, engenheiros e donos de conservadoras que sentiam na pele a escassez de mão de obra qualificada."
            </blockquote>
            
            <div className="space-y-10 relative z-10">
              <div className="flex gap-5">
                <div className="flex-shrink-0 mt-1">
                  <div className="w-12 h-12 bg-red-500/10 rounded-2xl flex items-center justify-center border border-red-500/20">
                    <Layers className="w-6 h-6 text-red-400" />
                  </div>
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-white mb-2">O Problema</h4>
                  <p className="text-slate-400 leading-relaxed">
                    Novas placas e inversores surgem todos os dias. Isso gera dependência de terceirizados caros e aumenta o tempo de elevador parado.
                  </p>
                </div>
              </div>

              <div className="flex gap-5">
                <div className="flex-shrink-0 mt-1">
                  <div className="w-12 h-12 bg-green-500/10 rounded-2xl flex items-center justify-center border border-green-500/20">
                    <ShieldCheck className="w-6 h-6 text-green-400" />
                  </div>
                </div>
                <div>
                  <h4 className="text-xl font-semibold text-white mb-2">A Solução</h4>
                  <p className="text-slate-400 leading-relaxed">
                    Uma central de inteligência na palma da mão. Democratizamos o conhecimento para que sua empresa tenha autonomia e segurança.
                  </p>
                </div>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-800 h-full min-h-[400px] lg:min-h-[600px] relative flex items-center justify-center overflow-hidden">
            <img 
              src="https://images.unsplash.com/photo-1677442136019-21780ecad995?w=800&h=800&fit=crop&q=80" 
              alt="Inteligência Artificial e Tecnologia" 
              className="w-full h-full object-cover opacity-30 mix-blend-luminosity"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-transparent to-transparent lg:bg-gradient-to-l"></div>
            
            {/* AI circuit overlay */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500/20 blur-[100px] rounded-full"></div>
                <svg viewBox="0 0 200 200" className="w-64 h-64 text-blue-400 opacity-40 relative z-10 animate-[spin_60s_linear_infinite]">
                  <circle cx="100" cy="100" r="80" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 8"/>
                  <circle cx="100" cy="100" r="60" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="8 4"/>
                  <circle cx="100" cy="100" r="40" fill="none" stroke="currentColor" strokeWidth="1" strokeDasharray="4 6"/>
                  <circle cx="100" cy="100" r="6" fill="currentColor" opacity="0.8"/>
                  <line x1="100" y1="40" x2="100" y2="20" stroke="currentColor" strokeWidth="1.5"/>
                <circle cx="100" cy="16" r="4" fill="currentColor" opacity="0.6"/>
                <line x1="100" y1="160" x2="100" y2="180" stroke="currentColor" strokeWidth="1.5"/>
                <circle cx="100" cy="184" r="4" fill="currentColor" opacity="0.6"/>
                <line x1="40" y1="100" x2="20" y2="100" stroke="currentColor" strokeWidth="1.5"/>
                <circle cx="16" cy="100" r="4" fill="currentColor" opacity="0.6"/>
                <line x1="160" y1="100" x2="180" y2="100" stroke="currentColor" strokeWidth="1.5"/>
                <circle cx="184" cy="100" r="4" fill="currentColor" opacity="0.6"/>
                <line x1="58" y1="58" x2="40" y2="40" stroke="currentColor" strokeWidth="1"/>
                <circle cx="36" cy="36" r="3" fill="currentColor" opacity="0.5"/>
                <line x1="142" y1="58" x2="160" y2="40" stroke="currentColor" strokeWidth="1"/>
                <circle cx="164" cy="36" r="3" fill="currentColor" opacity="0.5"/>
                <line x1="58" y1="142" x2="40" y2="160" stroke="currentColor" strokeWidth="1"/>
                <circle cx="36" cy="164" r="3" fill="currentColor" opacity="0.5"/>
                <line x1="142" y1="142" x2="160" y2="160" stroke="currentColor" strokeWidth="1"/>
                <circle cx="164" cy="164" r="3" fill="currentColor" opacity="0.5"/>
              </svg>
              </div>
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent"></div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default Features;