import React, { useEffect, useState } from 'react';
import { Check } from 'lucide-react';
import * as Storage from '../services/storage';

export interface Plan {
  id: string;
  name: string;
  price: number;
  period: string;
  features: string[];
  queries: string;
  devices: string;
  popular?: boolean;
}

export const PLANS: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    period: 'mês',
    queries: '1 consulta a cada 24h',
    devices: '1 dispositivo',
    features: ['1 consulta a cada 24h', '1 dispositivo', 'Acesso básico'],
    popular: false
  },
  {
    id: 'iniciante',
    name: 'Iniciante',
    price: 9.99,
    period: 'mês',
    queries: '5 consultas a cada 24h',
    devices: '1 dispositivo',
    features: ['5 consultas a cada 24h', '1 dispositivo', 'Histórico de 7 dias'],
    popular: false
  },
  {
    id: 'profissional',
    name: 'Profissional',
    price: 19.99,
    period: 'mês',
    queries: 'Consultas ilimitadas',
    devices: '1 dispositivo',
    features: ['Consultas ilimitadas', '1 dispositivo', 'Suporte prioritário', 'Histórico completo'],
    popular: true
  },
  {
    id: 'empresa',
    name: 'Empresa',
    price: 99.99,
    period: 'mês',
    queries: 'Consultas ilimitadas',
    devices: 'Até 5 dispositivos',
    features: ['Consultas ilimitadas', 'Até 5 dispositivos', 'Logins simultâneos', 'Dashboard de gestão'],
    popular: false
  }
];

interface PricingProps {
  onSelectPlan: (plan: Plan) => void;
}

const Pricing: React.FC<PricingProps> = ({ onSelectPlan }) => {
  const [plans, setPlans] = useState<Plan[]>(PLANS);

  useEffect(() => {
    const dynamicPlans = Storage.getPublicPlans();
    if (Array.isArray(dynamicPlans) && dynamicPlans.length > 0) {
      setPlans(dynamicPlans as Plan[]);
    }
  }, []);

  return (
    <div id='pricing' className='py-24 bg-slate-50 relative overflow-hidden'>
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-gradient-to-b from-blue-100/50 to-transparent rounded-full blur-3xl"></div>
      </div>

      <div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10'>
        <div className='text-center max-w-3xl mx-auto mb-20'>
          <h2 className='text-base font-semibold text-blue-600 tracking-wide uppercase mb-3'>Investimento</h2>
          <p className='text-3xl font-extrabold text-slate-900 sm:text-4xl lg:text-5xl tracking-tight mb-6'>
            Planos Simples e Transparentes
          </p>
          <p className='text-lg sm:text-xl text-slate-600'>
            Escolha o plano ideal para suas necessidades. Sem taxas ocultas, cancele quando quiser.
          </p>
        </div>

        <div className='grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-8 max-w-7xl mx-auto'>
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative flex flex-col p-8 rounded-3xl transition-all duration-300 ${plan.popular ? 'border-2 border-blue-600 shadow-2xl shadow-blue-500/20 bg-white md:-translate-y-4 z-10' : 'border border-slate-200 bg-white shadow-lg shadow-slate-200/50 hover:shadow-xl hover:-translate-y-1'}`}
            >
              {plan.popular && (
                <div className='absolute -top-4 left-1/2 transform -translate-x-1/2 bg-gradient-to-r from-blue-600 to-blue-400 text-white px-6 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider shadow-md'>
                  Mais Popular
                </div>
              )}

              <div className='mb-8'>
                <h3 className='text-xl font-bold text-slate-900 mb-2'>{plan.name}</h3>
                <div className='mt-4 flex items-baseline text-slate-900'>
                  <span className='text-5xl font-extrabold tracking-tight'>
                    {plan.price === 0 ? 'Grátis' : `R$ ${plan.price.toFixed(2).replace('.', ',')}`}
                  </span>
                  {plan.price > 0 && <span className='ml-2 text-lg font-medium text-slate-500'>/{plan.period}</span>}
                </div>
              </div>

              <ul className='flex-1 space-y-4 mb-8'>
                {plan.features.map((feature, idx) => (
                  <li key={idx} className='flex items-start'>
                    <div className={`flex-shrink-0 mt-0.5 p-1 rounded-full ${plan.popular ? 'bg-blue-100 text-blue-600' : 'bg-blue-50 text-blue-600'}`}>
                      <Check className='h-3 w-3' />
                    </div>
                    <span className='ml-3 text-slate-600 text-sm leading-relaxed'>{feature}</span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => onSelectPlan(plan)}
                className={`w-full py-3.5 px-4 rounded-xl font-bold transition-all transform hover:-translate-y-0.5 ${plan.popular ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg shadow-blue-500/30' : 'bg-slate-100 text-slate-800 hover:bg-slate-200 hover:shadow-md'}`}
              >
                {plan.id === 'free'
                  ? 'Começar Grátis'
                  : `Assinar ${plan.name}`}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Pricing;
