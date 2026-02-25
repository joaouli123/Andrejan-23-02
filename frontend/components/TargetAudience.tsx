import React from 'react';
import { Briefcase, Award, TrendingUp, DollarSign, Clock, Lock, ShieldCheck, Users } from 'lucide-react';

const TargetAudience: React.FC = () => {
  return (
    <div id="audience" className="py-24 bg-white relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-slate-50 rounded-full blur-3xl opacity-50"></div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-20">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-600 text-xs font-bold tracking-wide uppercase mb-4">
            <Users className="w-3 h-3 mr-2" />
            Público Alvo
          </div>
          <h2 className="text-3xl font-extrabold text-slate-900 sm:text-4xl lg:text-5xl tracking-tight mb-6">Para Quem é a Elevex?</h2>
          <p className="text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto">Soluções personalizadas para cada perfil do setor de transporte vertical.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 lg:gap-10">
          
          {/* Owners */}
          <div className="bg-white rounded-3xl shadow-lg shadow-slate-200/50 border border-slate-100 p-8 hover:shadow-xl hover:-translate-y-2 transition-all duration-300 group">
            <div className="flex items-center justify-center w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl mb-8 group-hover:scale-110 transition-transform duration-300">
              <Briefcase className="w-8 h-8" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-6">Donos de Empresas</h3>
            <ul className="space-y-5">
              <li className="flex items-start">
                <div className="bg-blue-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <DollarSign className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Redução de Custos</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Corte gastos com terceirização especializada.</span>
                </div>
              </li>
              <li className="flex items-start">
                <div className="bg-blue-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <Clock className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Eficiência</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Diminua o tempo de atendimento dos chamados.</span>
                </div>
              </li>
              <li className="flex items-start">
                <div className="bg-blue-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <Lock className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Autonomia</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Capacite sua equipe interna.</span>
                </div>
              </li>
            </ul>
          </div>

          {/* Experienced Techs */}
          <div className="bg-white rounded-3xl shadow-lg shadow-slate-200/50 border border-slate-100 p-8 hover:shadow-xl hover:-translate-y-2 transition-all duration-300 group relative">
             <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-blue-600 to-cyan-500 text-white px-4 py-1 rounded-full text-xs font-bold uppercase tracking-wider shadow-md">
               Mais Usado
             </div>
             <div className="flex items-center justify-center w-16 h-16 bg-amber-50 text-amber-600 rounded-2xl mb-8 group-hover:scale-110 transition-transform duration-300 mt-2">
              <Award className="w-8 h-8" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-6">Técnicos Experientes</h3>
             <ul className="space-y-5">
              <li className="flex items-start">
                <div className="bg-amber-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <TrendingUp className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Atualização</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Suporte para marcas novas e modelos importados.</span>
                </div>
              </li>
              <li className="flex items-start">
                <div className="bg-amber-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <Clock className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Agilidade</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Diagnostique falhas raras rapidamente.</span>
                </div>
              </li>
               <li className="flex items-start">
                <div className="bg-amber-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <Award className="w-4 h-4 text-amber-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Especialize-se</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Torne-se a referência técnica da sua região.</span>
                </div>
              </li>
            </ul>
          </div>

          {/* Beginners */}
          <div className="bg-white rounded-3xl shadow-lg shadow-slate-200/50 border border-slate-100 p-8 hover:shadow-xl hover:-translate-y-2 transition-all duration-300 group">
             <div className="flex items-center justify-center w-16 h-16 bg-green-50 text-green-600 rounded-2xl mb-8 group-hover:scale-110 transition-transform duration-300">
              <TrendingUp className="w-8 h-8" />
            </div>
            <h3 className="text-2xl font-bold text-slate-900 mb-6">Técnicos Iniciantes</h3>
             <ul className="space-y-5">
              <li className="flex items-start">
                <div className="bg-green-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <TrendingUp className="w-4 h-4 text-green-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Acelerador</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Funciona como um mentor digital no bolso.</span>
                </div>
              </li>
               <li className="flex items-start">
                <div className="bg-green-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <ShieldCheck className="w-4 h-4 text-green-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Segurança</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Tenha confiança para atender chamados.</span>
                </div>
              </li>
               <li className="flex items-start">
                <div className="bg-green-50 p-1.5 rounded-lg mr-3 mt-0.5">
                  <DollarSign className="w-4 h-4 text-green-600" />
                </div>
                <div>
                  <span className="font-bold text-slate-900 block mb-1">Reconhecimento</span>
                  <span className="text-sm text-slate-600 leading-relaxed">Aumente taxa de sucesso e conquiste melhores salários.</span>
                </div>
              </li>
            </ul>

          </div>

        </div>
      </div>
    </div>
  );
};

export default TargetAudience;