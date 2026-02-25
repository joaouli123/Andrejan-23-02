import React, { useState } from 'react';
import { ArrowLeft, Check, Eye, EyeOff, Building, Mail, User, Lock } from 'lucide-react';
import { Plan } from './Pricing';

interface RegisterProps {
  plan: Plan;
  onSuccess: (data: any) => void;
  onBack: () => void;
}

const Register: React.FC<RegisterProps> = ({ plan, onSuccess, onBack }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    company: '',
    password: '',
    confirmPassword: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[name];
        return newErrors;
      });
    }
  };

  const validate = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.name) newErrors.name = 'Nome é obrigatório';
    if (!formData.email) newErrors.email = 'Email é obrigatório';
    if (!/\S+@\S+\.\S+/.test(formData.email)) newErrors.email = 'Email inválido';
    if (!formData.password) newErrors.password = 'Senha é obrigatória';
    if (formData.password.length < 6) newErrors.password = 'A senha deve ter pelo menos 6 caracteres';
    if (formData.password !== formData.confirmPassword) newErrors.confirmPassword = 'As senhas não coincidem';
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSuccess(formData);
    }
  };

  return (
    <div className='min-h-screen bg-slate-50 flex'>
      {/* Left Side - Form */}
      <div className='flex-1 flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-20 xl:px-24'>
        <div className='mx-auto w-full max-w-md lg:w-[400px]'>
          <button 
            onClick={onBack}
            className='inline-flex items-center text-sm font-medium text-slate-500 hover:text-blue-600 mb-8 transition-colors bg-white px-4 py-2 rounded-full border border-slate-200 shadow-sm hover:shadow'
          >
            <ArrowLeft className='h-4 w-4 mr-2' />
            Voltar aos planos
          </button>
          
          <div>
            <h2 className='text-3xl font-extrabold text-slate-900 tracking-tight'>Crie sua conta</h2>
            <p className='mt-2 text-base text-slate-600'>
              Você está assinando o plano <span className='font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md'>{plan.name}</span>
            </p>
          </div>

          <div className='mt-10'>
            <form onSubmit={handleSubmit} className='space-y-5'>
              <div>
                <label htmlFor='name' className='block text-sm font-medium text-slate-700 mb-1.5'>
                  Nome completo
                </label>
                <div className='relative rounded-xl shadow-sm'>
                  <div className='absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none'>
                    <User className='h-5 w-5 text-slate-400' />
                  </div>
                  <input
                    id='name'
                    name='name'
                    type='text'
                    autoComplete='name'
                    required
                    value={formData.name}
                    onChange={handleChange}
                    className={`block w-full pl-11 pr-4 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white ${errors.name ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    placeholder='Seu nome'
                  />
                </div>
                {errors.name && <p className='mt-1.5 text-sm text-red-600 font-medium'>{errors.name}</p>}
              </div>

              <div>
                <label htmlFor='email' className='block text-sm font-medium text-slate-700 mb-1.5'>
                  Email profissional
                </label>
                <div className='relative rounded-xl shadow-sm'>
                  <div className='absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none'>
                    <Mail className='h-5 w-5 text-slate-400' />
                  </div>
                  <input
                    id='email'
                    name='email'
                    type='email'
                    autoComplete='email'
                    required
                    value={formData.email}
                    onChange={handleChange}
                    className={`block w-full pl-11 pr-4 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white ${errors.email ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    placeholder='voce@empresa.com'
                  />
                </div>
                {errors.email && <p className='mt-1.5 text-sm text-red-600 font-medium'>{errors.email}</p>}
              </div>

              <div>
                <label htmlFor='company' className='block text-sm font-medium text-slate-700 mb-1.5'>
                  Empresa <span className="text-slate-400 font-normal">(Opcional)</span>
                </label>
                <div className='relative rounded-xl shadow-sm'>
                  <div className='absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none'>
                    <Building className='h-5 w-5 text-slate-400' />
                  </div>
                  <input
                    id='company'
                    name='company'
                    type='text'
                    value={formData.company}
                    onChange={handleChange}
                    className='block w-full pl-11 pr-4 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white'
                    placeholder='Sua empresa'
                  />
                </div>
              </div>

              <div>
                <label htmlFor='password' className='block text-sm font-medium text-slate-700 mb-1.5'>
                  Senha
                </label>
                <div className='relative rounded-xl shadow-sm'>
                  <div className='absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none'>
                    <Lock className='h-5 w-5 text-slate-400' />
                  </div>
                  <input
                    id='password'
                    name='password'
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={formData.password}
                    onChange={handleChange}
                    className={`block w-full pl-11 pr-12 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white ${errors.password ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    placeholder='••••••••'
                  />
                  <div className='absolute inset-y-0 right-0 pr-3 flex items-center'>
                    <button
                      type='button'
                      onClick={() => setShowPassword(!showPassword)}
                      className='text-slate-400 hover:text-blue-600 focus:outline-none p-1 rounded-md transition-colors'
                    >
                      {showPassword ? <EyeOff className='h-5 w-5' /> : <Eye className='h-5 w-5' />}
                    </button>
                  </div>
                </div>
                {errors.password && <p className='mt-1.5 text-sm text-red-600 font-medium'>{errors.password}</p>}
              </div>

              <div>
                <label htmlFor='confirmPassword' className='block text-sm font-medium text-slate-700 mb-1.5'>
                  Confirmar Senha
                </label>
                <div className='relative rounded-xl shadow-sm'>
                  <div className='absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none'>
                    <Lock className='h-5 w-5 text-slate-400' />
                  </div>
                  <input
                    id='confirmPassword'
                    name='confirmPassword'
                    type='password'
                    required
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className={`block w-full pl-11 pr-4 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white ${errors.confirmPassword ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : ''}`}
                    placeholder='••••••••'
                  />
                </div>
                {errors.confirmPassword && <p className='mt-1.5 text-sm text-red-600 font-medium'>{errors.confirmPassword}</p>}
              </div>

              <div className="pt-4">
                <button
                  type='submit'
                  className='w-full flex justify-center items-center py-3.5 px-4 border border-transparent rounded-xl shadow-lg shadow-blue-500/30 text-sm font-bold text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all transform hover:-translate-y-0.5'
                >
                  Continuar para Pagamento
                  <ArrowRight className="ml-2 h-4 w-4" />
                </button>
                <p className="text-center text-xs text-slate-500 mt-4">
                  Ao continuar, você concorda com nossos Termos de Serviço e Política de Privacidade.
                </p>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Right Side - Summary */}
      <div className='hidden lg:flex relative flex-1 bg-slate-900 overflow-hidden'>
        {/* Background decorations */}
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute -top-[20%] -right-[10%] w-[70%] h-[70%] rounded-full bg-blue-600/20 blur-[100px]" />
          <div className="absolute -bottom-[20%] -left-[10%] w-[60%] h-[60%] rounded-full bg-cyan-600/20 blur-[100px]" />
        </div>

        <div className='relative w-full flex flex-col justify-center items-center text-white p-12'>
            <div className='max-w-md w-full space-y-8'>
                 <div>
                    <div className="inline-flex items-center px-3 py-1 rounded-full bg-blue-500/20 border border-blue-500/30 text-blue-300 text-xs font-semibold mb-6">
                      Resumo do Pedido
                    </div>
                    <h3 className='text-4xl font-extrabold tracking-tight'>Plano {plan.name}</h3>
                    <p className='mt-4 text-slate-300 text-lg leading-relaxed'>
                        Você está a um passo de transformar a manutenção de elevadores na sua empresa.
                    </p>
                 </div>

                 <div className='bg-slate-800/50 backdrop-blur-xl rounded-2xl p-8 border border-slate-700/50 shadow-2xl'>
                    <div className='flex justify-between items-end mb-6 pb-6 border-b border-slate-700/50'>
                         <div>
                           <span className='block text-sm font-medium text-slate-400 mb-1'>Investimento</span>
                           <span className='text-4xl font-bold text-white'>R$ {plan.price.toFixed(2).replace('.', ',')}</span>
                           <span className='text-base font-normal text-slate-400 ml-1'>/{plan.period}</span>
                         </div>
                    </div>
                    
                    <div className="space-y-4">
                      <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">O que está incluído:</h4>
                      <ul className='space-y-3'>
                          {plan.features.map((feature, idx) => (
                              <li key={idx} className='flex items-start text-slate-300'>
                                  <div className="flex-shrink-0 mt-0.5 bg-blue-500/20 p-1 rounded-full mr-3">
                                    <Check className='h-3 w-3 text-blue-400' />
                                  </div>
                                  <span className="text-sm leading-relaxed">{feature}</span>
                              </li>
                          ))}
                      </ul>
                    </div>
                 </div>
                 
                 {/* Trust indicators */}
                 <div className="flex items-center justify-center gap-6 pt-8 opacity-60">
                   <div className="flex items-center gap-2">
                     <Lock className="w-4 h-4" />
                     <span className="text-xs font-medium">Pagamento Seguro</span>
                   </div>
                   <div className="w-1 h-1 rounded-full bg-slate-600"></div>
                   <div className="flex items-center gap-2">
                     <Check className="w-4 h-4" />
                     <span className="text-xs font-medium">Cancelamento Fácil</span>
                   </div>
                 </div>
            </div>
        </div>
      </div>
    </div>
  );
};

export default Register;