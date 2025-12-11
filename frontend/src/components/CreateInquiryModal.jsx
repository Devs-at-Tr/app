import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Search } from 'lucide-react';
import { cn } from '../lib/utils';
import { API } from '../App';

const NO_VENUE_VALUE = 'no-venue';

const AUTOFILL_PROPS = {
  autoComplete: 'off',
  autoCorrect: 'off',
  autoCapitalize: 'off',
  spellCheck: false,
  name: 'no-autofill',
};

const TextInputWithClear = ({
  value,
  onChange,
  placeholder = '',
  type = 'text',
  className = '',
  onBlur,
  ariaLabel,
  ...rest
}) => {
  const inputRef = useRef(null);
  const showClear = Boolean(value);

  const handleClear = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onChange?.({ target: { value: '' } });
    // keep focus on the input
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  return (
    <div className="relative">
      <Input
        ref={inputRef}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        type={type}
        onBlur={onBlur}
        className={className}
        {...AUTOFILL_PROPS}
        {...rest}
      />
      {showClear && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute inset-y-0 right-2 flex items-center text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)] focus:outline-none"
          aria-label={ariaLabel || 'Clear field'}
        >
          ×
        </button>
      )}
    </div>
  );
};

const SearchableSelect = ({
  options = [],
  value,
  onChange,
  placeholder = 'Select...',
  disabled = false,
  busy = false,
  openOnFocus = true,
  hasError = false,
  onBlur: onBlurProp,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  const selectedLabel = useMemo(() => {
    const found = options.find((opt) => String(opt.value) === String(value));
    return found?.label || '';
  }, [options, value]);

  const filtered = useMemo(() => {
    const term = query.toLowerCase();
    const numericTerm = query.replace(/[^\d]/g, '');
    return options.filter((opt) => {
      const label = (opt.label || '').toLowerCase();
      const valueStr = String(opt.value ?? '').toLowerCase();
      const labelDigits = (opt.label || '').replace(/[^\d]/g, '');
      const valueDigits = String(opt.value ?? '').replace(/[^\d]/g, '');
      return (
        label.includes(term) ||
        valueStr.includes(term) ||
        (numericTerm &&
          (labelDigits.includes(numericTerm) || valueDigits.includes(numericTerm)))
      );
    });
  }, [options, query]);

  useEffect(() => {
    setQuery(selectedLabel);
  }, [selectedLabel]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (val, label) => {
    onChange?.(val);
    setQuery(label || '');
    setOpen(false);
  };

  const handleBlur = () => {
    setTimeout(() => {
      const active = document.activeElement;
      if (containerRef.current && containerRef.current.contains(active)) {
        return;
      }
      if (query && query !== selectedLabel) {
        setQuery('');
        if (value) {
          onChange?.(null);
        }
      }
      setOpen(false);
      onBlurProp?.();
    }, 0);
  };

  return (
    <div className="relative" ref={containerRef}>
      <Input
        ref={inputRef}
        {...AUTOFILL_PROPS}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          if (openOnFocus) {
            setOpen(true);
          }
        }}
        onMouseDown={() => setOpen(true)}
        onBlur={handleBlur}
        placeholder={placeholder}
        disabled={disabled || busy}
        className={cn(
          value ? 'pr-8' : '',
          hasError
            ? 'border-red-500 focus-visible:ring-red-500 focus-visible:ring-2 focus-visible:ring-offset-0'
            : '',
        )}
      />
      {value && (
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            setQuery('');
            onChange?.(null);
            setOpen(true);
            setTimeout(() => {
              inputRef.current?.focus();
            }, 0);
          }}
          className="absolute inset-y-0 right-2 flex items-center text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)] focus:outline-none"
          aria-label="Clear selection"
        >
          ×
        </button>
      )}
      {open && !disabled && (
        <div className="absolute z-10 mt-1 w-full rounded-md border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] shadow-lg max-h-56 overflow-auto">
          {filtered.length > 0 ? (
            filtered.map((opt, idx) => {
              const key = `${opt.value ?? ''}-${opt.label ?? ''}-${idx}`;
              return (
              <button
                key={key}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => handleSelect(opt.value, opt.label)}
                className={`block w-full text-left px-3 py-2 text-sm hover:bg-[var(--tg-chat-hover)] ${
                  String(opt.value) === String(value) ? 'text-[var(--tg-accent-strong)]' : 'text-[var(--tg-text-primary)]'
                }`}
              >
                {opt.label}
              </button>
            );
            })
          ) : (
            <div className="px-3 py-2 text-sm text-[var(--tg-text-muted)]">No results found</div>
          )}
        </div>
      )}
    </div>
  );
};

const normalizeCountryCode = (value = '') => {
  const stripped = value.replace(/[^\d+]/g, '');
  const digitsOnly = stripped.replace(/\+/g, '');
  if (!digitsOnly) {
    return '';
  }
  return `+${digitsOnly}`;
};

const normalizeLocalPhoneNumber = (value = '') =>
  value.replace(/[^\d]/g, '').replace(/^0+/, '');

const buildE164Number = (countryCode, localNumber) => {
  const normalizedCode = normalizeCountryCode(countryCode);
  const normalizedLocal = normalizeLocalPhoneNumber(localNumber);
  if (!normalizedCode || !normalizedLocal) {
    return '';
  }
  return `${normalizedCode}${normalizedLocal}`;
};

const isValidE164Number = (value = '') => /^\+[1-9]\d{6,14}$/.test(value);

const formatDialCode = (value = '') => {
  const digits = String(value || '').replace(/[^\d]/g, '');
  return digits ? `+${digits}` : '';
};

const detectRegionFromLocales = (countries = []) => {
  const resolveRegion = (locale) => (locale?.split('-')[1] || '').toUpperCase();
  const locales = [];
  try {
    if (Array.isArray(navigator.languages)) {
      locales.push(...navigator.languages);
    }
    if (navigator.language) {
      locales.push(navigator.language);
    }
  } catch (e) {
    // ignore
  }
  locales.push(Intl.DateTimeFormat().resolvedOptions().locale || '');
  for (const locale of locales) {
    const region = resolveRegion(locale);
    if (region) {
      const match = countries.find((c) => c.iso2 === region);
      if (match?.phonecode) return match.phonecode;
    }
  }
  return null;
};

const detectRegionFromCountryTimezones = (countries = []) => {
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (!tz) return null;
    const match = countries.find((c) => Array.isArray(c.timezones) && c.timezones.includes(tz));
    if (match?.phonecode) return match.phonecode;
  } catch (e) {
    return null;
  }
  return null;
};

const detectRegionFromIP = async (countries = []) => {
  try {
    const res = await fetch('https://ipapi.co/json/');
    if (!res.ok) return null;
    const data = await res.json();
    const iso2 = (data?.country || data?.countryCode || '').toUpperCase();
    const tz = data?.timezone;

    if (iso2 && iso2.length === 2) {
      const matchByIso = countries.find((c) => c.iso2 === iso2);
      if (matchByIso?.phonecode) return matchByIso.phonecode;
    }

    if (tz) {
      const matchByTz = countries.find((c) => Array.isArray(c.timezones) && c.timezones.includes(tz));
      if (matchByTz?.phonecode) return matchByTz.phonecode;
    }
  } catch (e) {
    console.warn('IP country lookup failed', e);
  }
  return null;
};

const resolveBrowserDialCode = async (countries = []) => {
  const fromIp = await detectRegionFromIP(countries);
  if (fromIp) return fromIp;

  const fromCountryTimezone = detectRegionFromCountryTimezones(countries);
  if (fromCountryTimezone) return fromCountryTimezone;

  const fromLocale = detectRegionFromLocales(countries);
  if (fromLocale) return fromLocale;

  return null;
};

const splitFullName = (raw = '') => {
  const onlyAlnumSpaces = (raw || '').replace(/[^A-Za-z0-9\s]/g, '').trim();
  const cleaned = onlyAlnumSpaces.replace(/\s+/g, ' ');
  if (!cleaned) return { first: '', middle: '', last: '' };
  const parts = cleaned.split(' ');
  if (parts.length === 1) {
    return { first: parts[0], middle: '', last: '' };
  }
  if (parts.length === 2) {
    return { first: parts[0], middle: '', last: parts[1] };
  }
  return { first: parts[0], middle: parts.slice(1, -1).join(' '), last: parts[parts.length - 1] };
};

const CreateInquiryModal = ({
  isOpen,
  onClose,
  onSubmit,
  chat,
  chatDisplayName,
  showAssignmentInfo = true,
  selectChat,
  prefillData = {},
}) => {
  const todayStr = useMemo(() => new Date().toISOString().split('T')[0], []);
  const tomorrowStr = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().split('T')[0];
  }, []);
  const currentTimeStr = useMemo(() => {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }, []);

  const [inquiryNumber, setInquiryNumber] = useState('');
  const [inquiryNotes, setInquiryNotes] = useState('Inquiry from Ticklegram chat ');
  const [inquiryEmail, setInquiryEmail] = useState('');
  const [inquiryCity, setInquiryCity] = useState('');
  const [inquiryAddress, setInquiryAddress] = useState('');
  const [inquiryDob, setInquiryDob] = useState('');
  const [inquiryWhatsApp, setInquiryWhatsApp] = useState('');
  const [inquiryCountry, setInquiryCountry] = useState('');
  const [inquiryCountryCode, setInquiryCountryCode] = useState('+1');
  const [inquiryPhoneError, setInquiryPhoneError] = useState('');
  const [inquiryFirstName, setInquiryFirstName] = useState('');
  const [inquiryMiddleName, setInquiryMiddleName] = useState('');
  const [inquiryLastName, setInquiryLastName] = useState('');
  const [inquiryContact2CountryCode, setInquiryContact2CountryCode] = useState('');
  const [inquiryContact2Number, setInquiryContact2Number] = useState('');
  const [inquiryGender, setInquiryGender] = useState('male');
  const [inquiryVenue, setInquiryVenue] = useState('');
  const [selectedVenueId, setSelectedVenueId] = useState(null);
  const [inquiryPincode, setInquiryPincode] = useState('');
  const [inquiryType, setInquiryType] = useState(null);
  const [inquiryCategoryOptions, setInquiryCategoryOptions] = useState([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(false);
  const [inquiryDate, setInquiryDate] = useState(todayStr);
  const [inquirySource, setInquirySource] = useState('19');
  const [inquiryCampaign, setInquiryCampaign] = useState('');
  const [inquiryProgram, setInquiryProgram] = useState(null);
  const [followUpDate, setFollowUpDate] = useState(tomorrowStr);
  const [followUpTime, setFollowUpTime] = useState('11:00');
  const [inquiryStatus, setInquiryStatus] = useState('Not Contacted');
  const [followupInterestOptions, setFollowupInterestOptions] = useState([]);
  const [isLoadingFollowupInterest, setIsLoadingFollowupInterest] = useState(false);
  const [isBlogger, setIsBlogger] = useState(false);
  const [autoAssignInquiry, setAutoAssignInquiry] = useState(false);
  const [isFranchisee, setIsFranchisee] = useState(false);
  const [countryCodeManuallySet, setCountryCodeManuallySet] = useState(false);
  const [countryOptions, setCountryOptions] = useState([]);
  const [isLoadingCountries, setIsLoadingCountries] = useState(false);
  const [selectedCountryId, setSelectedCountryId] = useState('');
  const [cityOptions, setCityOptions] = useState([]);
  const [isLoadingCities, setIsLoadingCities] = useState(false);
  const [selectedCityId, setSelectedCityId] = useState('');
  const [venueOptions, setVenueOptions] = useState([]);
  const [isLoadingVenues, setIsLoadingVenues] = useState(false);
  const [venueError, setVenueError] = useState('');
  const [touched, setTouched] = useState({});
  const [attemptedSubmit, setAttemptedSubmit] = useState(false);
  const [hasAutoSetCountry, setHasAutoSetCountry] = useState(false);
  const [hasCategoryInteraction, setHasCategoryInteraction] = useState(false);
  const hasCountryOptions = countryOptions.length > 0;
  const [duplicateCheckStatus, setDuplicateCheckStatus] = useState(null); // null | 'ok' | 'duplicate' | 'error'
  const [duplicateCheckMessage, setDuplicateCheckMessage] = useState('');
  const [duplicateAgentEmpId, setDuplicateAgentEmpId] = useState(null);
  const [duplicateAgentName, setDuplicateAgentName] = useState(null);
  const [resolvedAgentName, setResolvedAgentName] = useState(null);
  const [assigningAgent, setAssigningAgent] = useState(false);
  const [assignError, setAssignError] = useState('');
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false);
  const [phoneValidationStatus, setPhoneValidationStatus] = useState(null); // null | 'valid' | 'invalid' | 'error'
  const [phoneValidationMessage, setPhoneValidationMessage] = useState('');
  const [isValidatingPhone, setIsValidatingPhone] = useState(false);
  const [followUpError, setFollowUpError] = useState('');
  const [isSubmittingInquiry, setIsSubmittingInquiry] = useState(false);
  const countryOptionsRef = useRef([]);

  const normalizedInquiryPhone = useMemo(
    () => buildE164Number(inquiryCountryCode, inquiryNumber),
    [inquiryCountryCode, inquiryNumber]
  );

  const inquiryPhoneIsValid = useMemo(
    () => isValidE164Number(normalizedInquiryPhone),
    [normalizedInquiryPhone]
  );

  const hasCountry = Boolean(selectedCountryId);
  const hasCity = hasCountry ? Boolean(selectedCityId) : false;
  const venueOk = venueOptions.length > 0 ? selectedVenueId !== null : Boolean(inquiryVenue);
  const followupOk = Boolean(followUpDate) && Boolean(followUpTime) && !followUpError;
  const inquiryDateOk = Boolean(inquiryDate);
  const categoryOk = Boolean(inquiryType);
  const statusOk = Boolean(inquiryStatus);
  const areaOk = selectedVenueId === NO_VENUE_VALUE ? Boolean((inquiryAddress || '').trim()) : true;
  const requiredFieldsOk =
    hasCountry &&
    hasCity &&
    venueOk &&
    areaOk &&
    followupOk &&
    inquiryDateOk &&
    categoryOk &&
    statusOk;

  const markTouched = (field) => setTouched((prev) => ({ ...prev, [field]: true }));

  const requiredErrors = useMemo(() => {
    const errors = {};
    if (!inquiryNumber || !inquiryPhoneIsValid) {
      errors.phone = !inquiryNumber ? 'Phone number is required' : 'Enter a valid phone number';
    }
    if (!selectedCountryId) {
      errors.country = 'Please select a country';
    }
    if (!selectedCityId) {
      errors.city = 'Please select a city';
    }
    if (!venueOk) {
      errors.venue = venueOptions.length > 0 ? 'Please select a venue' : 'Please enter a venue';
    }
    if (selectedVenueId === NO_VENUE_VALUE && !(inquiryAddress || '').trim()) {
      errors.area = 'Area is required when no venue is selected';
    }
    if (!inquiryType) {
      errors.category = 'Please choose a category';
    }
    if (!inquiryDate) {
      errors.inquiryDate = 'Please pick an inquiry date';
    }
    if (!followUpDate) {
      errors.followUpDate = 'Please pick a follow-up date';
    }
    if (!followUpTime) {
      errors.followUpTime = 'Please pick a follow-up time';
    }
    if (!inquiryStatus) {
      errors.status = 'Please select a status';
    }
    return errors;
  }, [
    inquiryNumber,
    inquiryPhoneIsValid,
    selectedCountryId,
    selectedCityId,
    venueOk,
    venueOptions.length,
    selectedVenueId,
    inquiryAddress,
    inquiryType,
    inquiryDate,
    followUpDate,
    followUpTime,
    inquiryStatus,
  ]);

  const shouldShowError = (field) => (attemptedSubmit || touched[field]) && requiredErrors[field];

  const isPhoneInvalid =
    phoneValidationStatus === 'invalid' ||
    phoneValidationStatus === 'error' ||
    Boolean(inquiryPhoneError) ||
    !inquiryPhoneIsValid;
  const hasDuplicateCheck = duplicateCheckStatus !== null;
  const canCreateInquiry =
    inquiryPhoneIsValid &&
    duplicateCheckStatus === 'ok' &&
    !isCheckingDuplicate &&
    !isPhoneInvalid &&
    !followUpError &&
    requiredFieldsOk;

  useEffect(() => {
    countryOptionsRef.current = countryOptions;
  }, [countryOptions]);

  useEffect(() => {
    if (!isOpen) {
      setTouched({});
      setAttemptedSubmit(false);
    }
  }, [isOpen]);

  const applyPhonePrefill = useCallback((rawPhone = '') => {
    const normalizedMatch = (rawPhone || '').replace(/[^\d+]/g, '');
    if (!normalizedMatch) {
      setInquiryNumber('');
      return;
    }
    const options = countryOptionsRef.current || [];
    if (normalizedMatch.startsWith('+') && options.length > 0) {
      const matchCountry = options
        .filter((c) => normalizedMatch.startsWith(c.phonecode))
        .sort((a, b) => (b.phonecode || '').length - (a.phonecode || '').length)[0];
      if (matchCountry?.phonecode) {
        setInquiryCountryCode(matchCountry.phonecode);
        const remainder = normalizedMatch.slice(matchCountry.phonecode.length);
        setInquiryNumber(normalizeLocalPhoneNumber(remainder));
        return;
      }
    }
    setInquiryNumber(normalizeLocalPhoneNumber(normalizedMatch));
  }, []);

  useEffect(() => {
    if (!prefillData || typeof prefillData !== 'object') return;
    if (Object.prototype.hasOwnProperty.call(prefillData, 'notes')) {
      setInquiryNotes(prefillData.notes || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'email')) {
      setInquiryEmail(prefillData.email || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'city')) {
      setInquiryCity(prefillData.city || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'address')) {
      setInquiryAddress(prefillData.address || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'firstName')) {
      setInquiryFirstName(prefillData.firstName || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'middleName')) {
      setInquiryMiddleName(prefillData.middleName || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'lastName')) {
      setInquiryLastName(prefillData.lastName || '');
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'countryCode')) {
      setInquiryCountryCode(prefillData.countryCode || '');
      setCountryCodeManuallySet(Boolean(prefillData.countryCode));
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'phone')) {
      applyPhonePrefill(prefillData.phone);
    }
    if (Object.prototype.hasOwnProperty.call(prefillData, 'number')) {
      setInquiryNumber(normalizeLocalPhoneNumber(prefillData.number || ''));
    }
  }, [prefillData, applyPhonePrefill]);

  useEffect(() => {
    if (!inquiryNumber && !inquiryCountryCode) {
      setInquiryPhoneError('');
      return;
    }
    if (!inquiryPhoneIsValid) {
      setInquiryPhoneError('Invalid phone number for the selected country code.');
    } else {
      setInquiryPhoneError('');
    }
  }, [inquiryNumber, inquiryCountryCode, inquiryPhoneIsValid]);

  useEffect(() => {
    setDuplicateCheckStatus(null);
    setDuplicateCheckMessage('');
  }, [inquiryNumber, inquiryCountryCode]);

  useEffect(() => {
    if (!isOpen || !chatDisplayName) return;
    const alreadyFilled = inquiryFirstName || inquiryMiddleName || inquiryLastName;
    if (alreadyFilled) return;
    const nameParts = splitFullName(chatDisplayName);
    setInquiryFirstName(nameParts.first);
    setInquiryMiddleName(nameParts.middle);
    setInquiryLastName(nameParts.last);
  }, [isOpen, chatDisplayName, inquiryFirstName, inquiryMiddleName, inquiryLastName]);

  useEffect(() => {
    if (!inquiryCountryCode && !inquiryNumber) {
      setPhoneValidationStatus(null);
      setPhoneValidationMessage('');
      return;
    }
    const local = normalizeLocalPhoneNumber(inquiryNumber);
    if (!local) {
      setPhoneValidationStatus('invalid');
      setPhoneValidationMessage('Enter a phone number');
      return;
    }
    const customHint = (() => {
      const ccDigits = (inquiryCountryCode || '').replace(/[^\d]/g, '');
      if (ccDigits === '91' && local.length !== 10) {
        return 'Indian numbers must be exactly 10 digits.';
      }
      if (local.length < 4) {
        return 'Number looks too short.';
      }
      return null;
    })();
    if (customHint) {
      setPhoneValidationStatus('invalid');
      setPhoneValidationMessage(customHint);
      setIsValidatingPhone(false);
      return;
    }
    const handle = setTimeout(async () => {
      setIsValidatingPhone(true);
      setPhoneValidationStatus(null);
      setPhoneValidationMessage('');
      try {
        const token = localStorage.getItem('token');
        const resp = await axios.post(
          `${API}/validate-phone`,
          {
            country_code: inquiryCountryCode,
            phone_number: local,
          },
          { headers: token ? { Authorization: `Bearer ${token}` } : undefined }
        );
        const data = resp.data || {};
        if (data.valid) {
          setPhoneValidationStatus('valid');
          setPhoneValidationMessage(data.formatted?.international || 'Valid phone number');
        } else {
          setPhoneValidationStatus('invalid');
          const friendly =
            customHint ||
            data.message ||
            'Enter a valid phone number with country code.';
          setPhoneValidationMessage(friendly);
        }
      } catch (error) {
        console.error('Phone validation failed', error);
        const detail =
          error.response?.data?.detail ||
          error.response?.data?.message ||
          error.message ||
          'Validation failed';
        setPhoneValidationStatus('error');
        setPhoneValidationMessage(detail);
      } finally {
        setIsValidatingPhone(false);
      }
    }, 400);
    return () => clearTimeout(handle);
  }, [inquiryCountryCode, inquiryNumber]);

  useEffect(() => {
    if (!followUpDate) {
      setFollowUpError('');
      return;
    }
    const now = new Date();
    const selectedDate = new Date(followUpDate);
    if (selectedDate < new Date(todayStr)) {
      setFollowUpError('Follow-up cannot be in the past.');
      return;
    }
    if (followUpDate === todayStr && followUpTime) {
      const [hh = '00', mm = '00'] = followUpTime.split(':');
      const selectedTime = new Date();
      selectedTime.setHours(Number(hh), Number(mm), 0, 0);
      if (selectedTime < now) {
        setFollowUpError('Follow-up time cannot be in the past.');
        return;
      }
    }
    setFollowUpError('');
  }, [followUpDate, followUpTime, todayStr]);

  const handleSubmitInquiry = useCallback(async () => {
    setAttemptedSubmit(true);
    if (!requiredFieldsOk) {
      if (!followUpDate || !followUpTime) {
        setFollowUpError((prev) => prev || 'Please select follow-up date and time.');
      }
      return;
    }
    // Enforce dropdown-only values for country, city, and venue (when options exist)
    const countryMatch = countryOptions.find((c) => String(c.id) === String(selectedCountryId));
    const cityMatch = cityOptions.find((c) => String(c.id) === String(selectedCityId));
    const venueMatch =
      venueOptions.length > 0
        ? venueOptions.find((v) => String(v.id) === String(selectedVenueId))
        : null;

    if (!countryMatch) {
      setSelectedCountryId('');
      setInquiryCountry('');
    } else {
      setInquiryCountry(countryMatch.name || '');
    }

    if (!cityMatch) {
      setSelectedCityId('');
      setInquiryCity('');
    } else {
      setInquiryCity(cityMatch.name || '');
    }

    if (venueOptions.length > 0) {
      if (!venueMatch) {
        setSelectedVenueId('');
        setInquiryVenue('');
      } else {
        setInquiryVenue(venueMatch.name || venueMatch.rawVenue || '');
      }
    }

    if (!inquiryPhoneIsValid || isPhoneInvalid) {
      setInquiryPhoneError('Please enter a valid phone number before creating an inquiry.');
      return;
    }
    if (duplicateCheckStatus !== 'ok') {
      setInquiryPhoneError('Please run duplicate check and ensure the number is available.');
      return;
    }
    if (followUpError) {
      return;
    }
    setIsSubmittingInquiry(true);
    try {
      const token = localStorage.getItem('token');
      const toDDMMYYYY = (val) => {
        if (!val) return '';
        const [y, m, d] = val.split('-');
        return `${d}-${m}-${y}`;
      };
      const venueIdForPayload =
        selectedVenueId === NO_VENUE_VALUE
          ? 0
          : selectedVenueId !== null
            ? Number(selectedVenueId)
            : '';

      const inquiryPayload = {
        gender: inquiryGender === 'male' ? 'M' : inquiryGender === 'female' ? 'F' : 'O',
        source: '19',
        auto_assign_inq: autoAssignInquiry ? '1' : '0',
        employee_id: duplicateAgentEmpId || '',
        lname: inquiryLastName || '',
        mname: inquiryMiddleName || '',
        country_code: inquiryCountryCode || '',
        country_code_2: inquiryContact2CountryCode || inquiryCountryCode || '',
        doi_ui: inquiryDate ? toDDMMYYYY(inquiryDate) : '',
        doi: inquiryDate || '',
        mobile: normalizeLocalPhoneNumber(inquiryNumber),
        fname: inquiryFirstName || '',
        category_id: inquiryProgram !== null ? Number(inquiryProgram) : '',
        dob: inquiryDob || '',
        heard_from: inquiryCampaign || '',
        mobile2: normalizeLocalPhoneNumber(inquiryContact2Number),
        email: inquiryEmail || '',
        city: inquiryCity || '',
        country: inquiryCountry || '',
        venue_id: venueIdForPayload,
        category: inquiryProgram !== null ? [Number(inquiryProgram)] : [],
      };

      const followupPayload = {
        interest_string: inquiryStatus || 'Not Contacted',
        preferences: '',
        slot: '',
        area: selectedVenueId === NO_VENUE_VALUE ? inquiryAddress || '' : '',
        pincode: inquiryPincode || '',
        employee_id: duplicateAgentEmpId || '',
        time: followUpTime ? `${followUpTime}:00` : '',
        reminder: followUpDate && followUpTime ? `${followUpDate} ${followUpTime}:00` : '',
        country: inquiryCountry || '',
        city: inquiryCity || '',
        venue_id: venueIdForPayload,
      };

      const payload = {
        inquiry: inquiryPayload,
        followup: followupPayload,
        contact_id: 0,
        comment: inquiryNotes || 'Inquiry from Ticklegram chat ',
        existingContact: false,
        updateContact: true,
      };

      await axios.post(`${API}/inquiries/insert`, payload, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      onSubmit?.(payload);
      onClose?.();
    } catch (err) {
      console.error('Inquiry creation failed', err);
      const detail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Failed to create inquiry';
      setInquiryPhoneError(detail);
    } finally {
      setIsSubmittingInquiry(false);
    }
  }, [
    API,
    autoAssignInquiry,
    duplicateAgentEmpId,
    duplicateCheckStatus,
    followUpDate,
    followUpError,
    followUpTime,
    inquiryAddress,
    inquiryCampaign,
    inquiryCity,
    inquiryContact2CountryCode,
    inquiryContact2Number,
    inquiryCountry,
    inquiryCountryCode,
    inquiryDate,
    inquiryDob,
    inquiryEmail,
    inquiryFirstName,
    inquiryGender,
    inquiryLastName,
    inquiryMiddleName,
    inquiryNotes,
    inquiryNumber,
    inquiryPhoneIsValid,
    inquiryPincode,
    inquiryProgram,
    inquirySource,
    inquiryStatus,
    inquiryVenue,
    isPhoneInvalid,
    onClose,
    onSubmit,
  ]);

  const fetchCountries = useCallback(async () => {
    setIsLoadingCountries(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/countries`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const mapped = (response.data || [])
        .map((country) => {
          const dial = formatDialCode(country.phonecode || country.code || country.phone || country.phone_code);
          if (!dial) {
            return null;
          }
          return {
            id: country.id || country.iso2 || dial,
            name: country.name || country.iso2 || dial,
            iso2: (country.iso2 || '').toUpperCase(),
            phonecode: dial,
            timezones: Array.isArray(country.timezones) ? country.timezones : [],
          };
        })
        .filter(Boolean);
      if (mapped.length > 0) {
        setCountryOptions(mapped);
      }
    } catch (error) {
      console.error('Error loading countries:', error);
    } finally {
      setIsLoadingCountries(false);
    }
  }, []);

  const fetchCategories = useCallback(async () => {
    setIsLoadingCategories(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/inquiry-categories`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const categories = (response.data?.data || []).map((c) => ({
        id: Number(c.id) || Number(c.category) || null,
        name: c.category || '',
      })).filter((c) => c.id !== null);
      setInquiryCategoryOptions(categories);
    } catch (error) {
      console.error('Error loading categories:', error);
      setInquiryCategoryOptions([]);
    } finally {
      setIsLoadingCategories(false);
    }
  }, []);

  const fetchFollowupInterests = useCallback(async () => {
    setIsLoadingFollowupInterest(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/followup-interests`, {
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      });
      const interests = (response.data?.data || []).map((c) => ({
        id: c.id || c.interest,
        name: c.interest || '',
      }));
      setFollowupInterestOptions(interests);
    } catch (error) {
      console.error('Error loading follow-up interests:', error);
      setFollowupInterestOptions([]);
    } finally {
      setIsLoadingFollowupInterest(false);
    }
  }, []);

  const fetchCities = useCallback(
    async (countryId) => {
      if (!countryId) {
        setCityOptions([]);
        return;
      }
      setIsLoadingCities(true);
      setCityOptions([]);
      setSelectedCityId('');
      setInquiryCity('');
      setVenueOptions([]);
      setSelectedVenueId(null);
      setInquiryVenue('');
      setVenueError('');
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API}/cities`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          params: { country: countryId }
        });
        const cities = (response.data?.data || []).map((c) => ({
          id: c.id,
          name: c.name,
        }));
        setCityOptions(cities);
      } catch (error) {
        console.error('Error loading cities:', error);
        setCityOptions([]);
      } finally {
        setIsLoadingCities(false);
      }
    },
    []
  );

  const fetchVenues = useCallback(
    async (cityName) => {
      if (!cityName) {
        setVenueOptions([]);
        setSelectedVenueId(null);
        setInquiryVenue('');
        return;
      }
      setIsLoadingVenues(true);
      setVenueOptions([]);
      setSelectedVenueId(null);
      setInquiryVenue('');
      setVenueError('');
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get(`${API}/venues`, {
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          params: { city: cityName }
        });
        const venues = (response.data?.data || []).map((v) => {
          const idNum = Number(v.id);
          return {
            id: Number.isFinite(idNum) ? idNum : null,
            name: v.display_name || v.venue || '',
            rawVenue: v.venue,
          };
        });
        const enhanced = [
          { id: NO_VENUE_VALUE, name: 'No Venue', rawVenue: '' },
          ...venues,
        ].filter((v) => v.id !== null);
        setVenueOptions(enhanced);
        if (enhanced.length > 0) {
          const first = enhanced[0];
          setSelectedVenueId(first.id);
          setInquiryVenue(first.name || first.rawVenue || '');
        }
      } catch (error) {
        console.error('Error loading venues:', error);
        setVenueOptions([]);
        setVenueError(error.response?.data?.detail || error.message || 'Failed to load venues');
      } finally {
        setIsLoadingVenues(false);
      }
    },
    []
  );

  useEffect(() => {
    fetchCountries();
    fetchCategories();
    fetchFollowupInterests();
  }, [fetchCountries, fetchCategories, fetchFollowupInterests]);

  useEffect(() => {
    if (hasCategoryInteraction) return;
    if (inquiryType || inquiryCategoryOptions.length === 0) return;
    const first = inquiryCategoryOptions[0];
    if (first?.id !== undefined && first?.id !== null) {
      setInquiryType(first.id);
      setInquiryProgram(first.id);
    }
  }, [hasCategoryInteraction, inquiryCategoryOptions, inquiryType]);

  useEffect(() => {
    if (countryCodeManuallySet || hasAutoSetCountry) return;
    if (!countryOptions.length) return;
    (async () => {
      const detected = await resolveBrowserDialCode(countryOptions);
      if (detected && detected !== inquiryCountryCode) {
        setInquiryCountryCode(detected);
      } else if (!detected && countryOptions[0]?.phonecode && countryOptions[0].phonecode !== inquiryCountryCode) {
        setInquiryCountryCode(countryOptions[0].phonecode);
      }
      setHasAutoSetCountry(true);
    })();
  }, [countryCodeManuallySet, countryOptions, inquiryCountryCode, hasAutoSetCountry]);

  useEffect(() => {
    if (selectedCountryId) {
      fetchCities(selectedCountryId);
    }
  }, [selectedCountryId, fetchCities]);

  const handleCheckDuplicate = useCallback(async () => {
    const local = normalizeLocalPhoneNumber(inquiryNumber);
    if (!local) {
      setDuplicateCheckStatus('error');
      setDuplicateCheckMessage('Enter a phone number to check');
      setDuplicateAgentEmpId(null);
      setDuplicateAgentName(null);
      setResolvedAgentName(null);
      return;
    }
    setIsCheckingDuplicate(true);
    setDuplicateCheckStatus(null);
    setDuplicateCheckMessage('');
    setDuplicateAgentEmpId(null);
    setDuplicateAgentName(null);
    setResolvedAgentName(null);
    setAssignError('');
    try {
      const token = localStorage.getItem('token');
      const resp = await axios.post(
        `${API}/admin/check-duplicate-mobile`,
        {
          mobile: local,
          country_code: inquiryCountryCode,
        },
        { headers: token ? { Authorization: `Bearer ${token}` } : undefined }
      );
      const data = resp.data || {};
      const isError = Number(data.error) === 1;
      const hasDupes = Array.isArray(data.data) && data.data.length > 0;
      const duplicateFound = isError || hasDupes;
      const firstEntry = Array.isArray(data.data) && data.data.length > 0 ? data.data[0] : {};
      const dataObject = !Array.isArray(data.data) && data.data && typeof data.data === 'object' ? data.data : {};
      const inferredEmpIdRaw =
        firstEntry?.c_employee_id ||
        firstEntry?.c_employeeid ||
        firstEntry?.employee_id ||
        firstEntry?.emp_id ||
        dataObject?.c_employee_id ||
        dataObject?.c_employeeid ||
        dataObject?.employee_id ||
        dataObject?.emp_id ||
        data.c_employee_id ||
        data.employee_id ||
        data.emp_id ||
        null;
      const inferredName =
        firstEntry?.employee_name ||
        firstEntry?.assigned_to_name ||
        dataObject?.employee_name ||
        dataObject?.assigned_to_name ||
        data.employee_name ||
        data.assigned_to_name ||
        null;
      setDuplicateAgentEmpId(inferredEmpIdRaw ? String(inferredEmpIdRaw).trim() : null);
      setDuplicateAgentName(inferredName || null);
      setResolvedAgentName(null);
      setDuplicateCheckStatus(duplicateFound ? 'duplicate' : 'ok');
      setDuplicateCheckMessage(
        duplicateFound
          ? data.message || data.error_msg || 'Number already exists in CRM.'
          : 'Number is available.'
      );
      if (inferredEmpIdRaw) {
        try {
          const agentsResp = await axios.get(`${API}/users/agents`, {
            headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            params: { include_inactive: true },
          });
          const match = (agentsResp.data || []).find((a) => {
            const empId = (a.emp_id || '').toString().trim().toLowerCase();
            return empId === String(inferredEmpIdRaw).trim().toLowerCase();
          });
          if (match?.name) {
            setResolvedAgentName(match.name);
          }
        } catch (lookupError) {
          console.warn('Agent lookup failed', lookupError);
        }
      }
    } catch (error) {
      console.error('Duplicate check failed', error);
      const detail =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        'Failed to check number';
      setDuplicateCheckStatus('error');
      setDuplicateCheckMessage(detail);
    } finally {
      setIsCheckingDuplicate(false);
    }
  }, [inquiryNumber, inquiryCountryCode]);

  useEffect(() => {
    const hasNumber = Boolean(normalizeLocalPhoneNumber(inquiryNumber));
    if (isOpen && hasNumber && !isCheckingDuplicate && !duplicateCheckStatus) {
      handleCheckDuplicate();
    }
  }, [isOpen, inquiryNumber, isCheckingDuplicate, duplicateCheckStatus, handleCheckDuplicate]);

  const handleAssignToEmpId = useCallback(async () => {
    if (!chat?.id || !duplicateAgentEmpId) {
      return;
    }
    setAssigningAgent(true);
    setAssignError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Missing auth token');
      }
      const agentsResp = await axios.get(`${API}/users/agents`, {
        headers: { Authorization: `Bearer ${token}` },
        params: { include_inactive: true },
      });
      const agentMatch = (agentsResp.data || []).find((a) => {
        const empId = (a.emp_id || '').toString().trim().toLowerCase();
        const name = (a.name || '').toString().trim().toLowerCase();
        const targetEmpId = duplicateAgentEmpId ? duplicateAgentEmpId.toString().trim().toLowerCase() : null;
        const targetName = duplicateAgentName ? duplicateAgentName.toString().trim().toLowerCase() : null;
        return (targetEmpId && empId && empId === targetEmpId) || (targetName && name && name === targetName);
      });
      if (!agentMatch) {
        setAssignError('Agent not found for this Employee ID.');
        return;
      }
      if (agentMatch.is_active === false) {
        setAssignError('Agent is inactive.');
        return;
      }

      await axios.post(
        `${API}/admin/assign-chat`,
        { chat_id: chat.id, employee_id: duplicateAgentEmpId || agentMatch.emp_id },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setAssignError('');
      setResolvedAgentName(agentMatch.name || null);
      if (typeof selectChat === 'function') {
        await selectChat(chat.id);
      }
    } catch (error) {
      console.error('Assignment failed', error);
      const detail = error.response?.data?.detail || error.message || 'Failed to assign chat';
      setAssignError(detail);
    } finally {
      setAssigningAgent(false);
    }
  }, [API, chat?.id, duplicateAgentEmpId, duplicateAgentName, selectChat]);

  const allowDuplicateAssignUI = useMemo(
    () => {
      if (duplicateCheckStatus === 'ok') {
        return false;
      }
      const currentEmpId = chat?.assigned_agent?.emp_id
        ? String(chat.assigned_agent.emp_id).trim().toLowerCase()
        : null;
      const targetEmpId = duplicateAgentEmpId
        ? String(duplicateAgentEmpId).trim().toLowerCase()
        : null;
      if (currentEmpId && targetEmpId && currentEmpId === targetEmpId) {
        return false;
      }
      return Boolean(duplicateAgentEmpId || duplicateAgentName) || showAssignmentInfo;
    },
    [chat?.assigned_agent?.emp_id, duplicateAgentEmpId, duplicateAgentName, showAssignmentInfo, duplicateCheckStatus]
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => (!open ? onClose?.() : null)}>
      <DialogContent className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)] sm:max-w-[900px] w-full max-h-[80vh] overflow-hidden flex flex-col p-0">
        <div className="sticky top-0 z-10 bg-[var(--tg-surface)] px-6 pt-4 pb-3 border-b border-[var(--tg-border-soft)]">
          <DialogHeader className="p-0">
            <DialogTitle>Create inquiry</DialogTitle>
            <DialogDescription className="text-[var(--tg-text-muted)]">
              Prefill a new inquiry with the detected phone number.
            </DialogDescription>
          </DialogHeader>
        </div>
        <form className="flex-1 overflow-y-auto px-6 py-4 modal-scroll" autoComplete="off">
          <div className="space-y-3">
            {/* Primary contact */}
            <div className="space-y-1">
              <label className="text-xs text-[var(--tg-text-secondary)]">Phone number *</label>
              <div className="flex gap-2 flex-wrap items-center">
                {hasCountryOptions ? (
                  <SearchableSelect
                    options={countryOptions.map((country) => ({
                      value: country.phonecode,
                      label: `${country.name} (${country.phonecode})`,
                    }))}
                    value={inquiryCountryCode}
                    onChange={(value) => {
                      setCountryCodeManuallySet(true);
                      setInquiryCountryCode(normalizeCountryCode(value || ''));
                    }}
                    onBlur={() => markTouched('phone')}
                    placeholder={isLoadingCountries ? 'Loading...' : 'Country code'}
                    disabled={isLoadingCountries}
                    busy={isLoadingCountries}
                    openOnFocus={false}
                  />
                ) : (
                  <Input
                    {...AUTOFILL_PROPS}
                    value={inquiryCountryCode}
                    onChange={(e) => {
                      setCountryCodeManuallySet(true);
                      setInquiryCountryCode(normalizeCountryCode(e.target.value));
                    }}
                    onBlur={() => markTouched('phone')}
                    inputMode="tel"
                    autoComplete="tel-country-code"
                    className="w-32"
                    placeholder={isLoadingCountries ? 'Loading...' : '+1'}
                  />
                )}
                <TextInputWithClear
                  value={inquiryNumber}
                  onChange={(e) => setInquiryNumber(normalizeLocalPhoneNumber(e.target.value))}
                  onBlur={() => markTouched('phone')}
                  inputMode="tel"
                  autoComplete="tel-national"
                  placeholder="5551234567"
                  ariaLabel="Clear phone number"
                  className={cn(
                    'flex-1 min-w-[220px]',
                    phoneValidationStatus === 'invalid' || inquiryPhoneError
                      ? 'border-red-500 focus-visible:ring-red-500 focus-visible:border-red-500'
                      : ''
                  )}
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCheckDuplicate}
                  disabled={
                    isCheckingDuplicate ||
                    !normalizeLocalPhoneNumber(inquiryNumber) ||
                    isPhoneInvalid ||
                    !inquiryPhoneIsValid
                  }
                  className="h-10 w-10 p-0 flex items-center justify-center"
                  title="Check duplicate"
                >
                  {isCheckingDuplicate ? (
                    <span className="text-xs">...</span>
                  ) : (
                    <Search className="w-4 h-4" />
                  )}
                </Button>
              </div>
              {shouldShowError('phone') && requiredErrors.phone && (
                <p className="text-xs text-amber-400">{requiredErrors.phone}</p>
              )}
              {!phoneValidationMessage && inquiryPhoneError && (
                <p className="text-xs text-amber-400">{inquiryPhoneError}</p>
              )}
              {!inquiryPhoneError && normalizedInquiryPhone && (
                <p className="text-[11px] text-[var(--tg-text-muted)]">
                  {/* Will save as {normalizedInquiryPhone} */}
                </p>
              )}
              {duplicateCheckMessage && (
                <p
                  className={`text-xs ${
                    duplicateCheckStatus === 'duplicate'
                      ? 'text-amber-400'
                      : duplicateCheckStatus === 'ok'
                        ? 'text-emerald-300'
                        : 'text-amber-400'
                  }`}
                >
                  {duplicateCheckMessage}
                </p>
              )}
              {/* {phoneValidationMessage && (
                <p
                  className={`text-xs ${
                    phoneValidationStatus === 'valid'
                      ? 'text-emerald-300'
                      : 'text-amber-400'
                  }`}
                >
                  {isValidatingPhone ? 'Validating...' : phoneValidationMessage}
                </p>
              )} */}
              {allowDuplicateAssignUI && (
                <div className="pt-1">
                  {hasDuplicateCheck && (
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="px-3 text-xs"
                        disabled={(!duplicateAgentEmpId && !duplicateAgentName) || assigningAgent}
                        onClick={handleAssignToEmpId}
                      >
                        {assigningAgent
                          ? 'Assigning...'
                          : `Assign to ${resolvedAgentName || duplicateAgentName || 'agent'}`}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="px-3 text-xs"
                        disabled={assigningAgent}
                      >
                        Assigned to Me
                      </Button>
                      {/* {(duplicateAgentEmpId || duplicateAgentName) && (
                        <span className="text-[11px] text-[var(--tg-text-muted)]">
                          {resolvedAgentName || duplicateAgentName || 'Matched agent'}
                        </span>
                      )} */}
                    </div>
                  )}
                  {hasDuplicateCheck && !duplicateAgentEmpId && !duplicateAgentName && !assignError && (
                    <p className="text-xs text-amber-400 mt-1">
                      Employee ID not provided in duplicate response; cannot auto-assign.
                    </p>
                  )}
                  {assignError && (
                    <p className="text-xs text-amber-400 mt-1">{assignError}</p>
                  )}
                </div>
              )}
            </div>
            {/* Extended inquiry fields */}
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">First name</label>
                <TextInputWithClear
                  value={inquiryFirstName}
                  onChange={(e) => setInquiryFirstName(e.target.value)}
                  onBlur={() => markTouched('firstName')}
                  placeholder="First"
                  ariaLabel="Clear first name"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Middle name</label>
                <TextInputWithClear
                  value={inquiryMiddleName}
                  onChange={(e) => setInquiryMiddleName(e.target.value)}
                  onBlur={() => markTouched('middleName')}
                  placeholder="Middle"
                  ariaLabel="Clear middle name"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Last name</label>
                <TextInputWithClear
                  value={inquiryLastName}
                  onChange={(e) => setInquiryLastName(e.target.value)}
                  onBlur={() => markTouched('lastName')}
                  placeholder="Last"
                  ariaLabel="Clear last name"
                />
              </div>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Contact 2 country code</label>
                {hasCountryOptions ? (
                  <SearchableSelect
                    options={countryOptions.map((country) => ({
                      value: country.phonecode,
                      label: `${country.name} (${country.phonecode})`,
                    }))}
                    value={inquiryContact2CountryCode || inquiryCountryCode}
                    onChange={(value) => setInquiryContact2CountryCode(normalizeCountryCode(value || ''))}
                    placeholder={isLoadingCountries ? 'Loading...' : 'Select country'}
                    disabled={isLoadingCountries}
                    busy={isLoadingCountries}
                  />
                ) : (
                  <Input
                    {...AUTOFILL_PROPS}
                    value={inquiryContact2CountryCode || inquiryCountryCode}
                    onChange={(e) => setInquiryContact2CountryCode(normalizeCountryCode(e.target.value))}
                    placeholder="+91"
                  />
                )}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Contact 2 mobile</label>
                <TextInputWithClear
                  value={inquiryContact2Number}
                  onChange={(e) => setInquiryContact2Number(normalizeLocalPhoneNumber(e.target.value))}
                  onBlur={() => markTouched('contact2')}
                  inputMode="tel"
                  placeholder="Alternate number"
                  ariaLabel="Clear alternate number"
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Gender</label>
                <div className="flex items-center gap-3 text-[var(--tg-text-secondary)] text-sm">
                  {['female', 'male', 'other'].map((val) => (
                    <label key={val} className="flex items-center gap-1 cursor-pointer">
                      <input
                        type="radio"
                        name="inquiry-gender"
                        value={val}
                        checked={inquiryGender === val}
                        onChange={() => setInquiryGender(val)}
                      />
                      <span className="capitalize">{val}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">DOB</label>
                <Input
                  {...AUTOFILL_PROPS}
                  type="date"
                  value={inquiryDob}
                  onChange={(e) => setInquiryDob(e.target.value)}
                  max={todayStr}
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Country *</label>
                <SearchableSelect
                  options={countryOptions.map((c) => ({ value: String(c.id), label: c.name }))}
                  value={selectedCountryId}
                  onChange={(value) => {
                    setSelectedCountryId(value);
                    const found = countryOptions.find((c) => String(c.id) === String(value));
                    setInquiryCountry(found?.name || '');
                  }}
                  onBlur={() => markTouched('country')}
                  hasError={shouldShowError('country')}
                  placeholder={isLoadingCountries ? 'Loading...' : 'Country'}
                  disabled={isLoadingCountries}
                  busy={isLoadingCountries}
                />
                {shouldShowError('country') && requiredErrors.country && (
                  <p className="text-xs text-amber-400">{requiredErrors.country}</p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">City *</label>
                <SearchableSelect
                  options={cityOptions.map((c) => ({ value: String(c.id), label: c.name }))}
                  value={selectedCityId}
                  onChange={(value) => {
                    setSelectedCityId(value);
                    const found = cityOptions.find((c) => String(c.id) === String(value));
                    const cityName = found?.name || '';
                    setInquiryCity(cityName);
                    fetchVenues(cityName);
                  }}
                  onBlur={() => markTouched('city')}
                  hasError={shouldShowError('city')}
                  placeholder={!selectedCountryId ? 'Select country first' : isLoadingCities ? 'Loading...' : 'City'}
                  disabled={!selectedCountryId || isLoadingCities}
                  busy={isLoadingCities || !selectedCountryId}
                />
                {shouldShowError('city') && requiredErrors.city && (
                  <p className="text-xs text-amber-400">{requiredErrors.city}</p>
                )}
              </div>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Venue *</label>
                {venueOptions.length > 0 ? (
                  <SearchableSelect
                    options={venueOptions.map((venue) => ({
                      value: venue.id,
                      label: venue.name || venue.rawVenue || `Venue ${venue.id}`,
                    }))}
                    value={selectedVenueId}
                    onChange={(value) => {
                      let nextVal = null;
                      if (value === NO_VENUE_VALUE) {
                        nextVal = NO_VENUE_VALUE;
                      } else if (value !== null && value !== undefined && value !== '') {
                        const num = Number(value);
                        nextVal = Number.isFinite(num) ? num : null;
                      }
                      setSelectedVenueId(nextVal);
                      const found = venueOptions.find((v) => String(v.id) === String(value));
                      setInquiryVenue(found?.name || found?.rawVenue || '');
                    }}
                    onBlur={() => markTouched('venue')}
                    hasError={shouldShowError('venue')}
                    placeholder={isLoadingVenues ? 'Loading...' : 'Select venue'}
                    disabled={isLoadingVenues}
                    busy={isLoadingVenues}
                  />
                ) : (
                  <TextInputWithClear
                    value={inquiryVenue}
                    onChange={(e) => setInquiryVenue(e.target.value)}
                    onBlur={() => markTouched('venue')}
                    placeholder={isLoadingVenues ? 'Loading venues...' : 'Enter venue'}
                    disabled={isLoadingVenues}
                    ariaLabel="Clear venue"
                    className={cn(
                      shouldShowError('venue')
                        ? 'border-red-500 focus-visible:ring-red-500 focus-visible:ring-2 focus-visible:ring-offset-0'
                        : ''
                    )}
                  />
                )}
                {String(selectedVenueId) === '0' ? (
                  <TextInputWithClear
                    value={inquiryAddress}
                    onChange={(e) => setInquiryAddress(e.target.value)}
                    onBlur={() => markTouched('area')}
                    placeholder="Enter area (required when no venue)"
                    ariaLabel="Clear area"
                    className={cn(
                      'mt-2',
                      shouldShowError('area')
                        ? 'border-red-500 focus-visible:ring-red-500 focus-visible:ring-2 focus-visible:ring-offset-0'
                        : ''
                    )}
                  />
                ) : null}
                {shouldShowError('venue') && requiredErrors.venue && (
                  <p className="text-xs text-amber-400">{requiredErrors.venue}</p>
                )}
                {shouldShowError('area') && requiredErrors.area && (
                  <p className="text-xs text-amber-400">{requiredErrors.area}</p>
                )}
                {venueError && <p className="text-xs text-amber-400">{venueError}</p>}
              </div>
              {/* <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Address</label>
                <Input
                  {...AUTOFILL_PROPS}
                  value={inquiryAddress}
                  onChange={(e) => setInquiryAddress(e.target.value)}
                  placeholder="Street, area, town"
                />
              </div> */}
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Pincode</label>
                <TextInputWithClear
                  value={inquiryPincode}
                  onChange={(e) => setInquiryPincode(e.target.value)}
                  onBlur={() => markTouched('pincode')}
                  placeholder="123456"
                  ariaLabel="Clear pincode"
                />
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-xs text-[var(--tg-text-secondary)]">Comment</label>
              <div className="relative">
                <textarea
                  {...AUTOFILL_PROPS}
                  value={inquiryNotes}
                  onChange={(e) => setInquiryNotes(e.target.value)}
                  onBlur={() => markTouched('comment')}
                  placeholder="Inquiry from Ticklegram chat"
                  className="w-full rounded-md border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-3 py-2 pr-8 text-sm text-[var(--tg-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:ring-[var(--tg-accent-soft)]"
                  rows={3}
                />
                {inquiryNotes && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setInquiryNotes('');
                    }}
                    className="absolute right-2 top-2 text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)] focus:outline-none"
                    aria-label="Clear comment"
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Inquiry (Select Category) *</label>
                <SearchableSelect
                  options={inquiryCategoryOptions.map((cat) => ({
                    value: cat.id,
                    label: cat.name,
                  }))}
                  value={inquiryType}
                  onChange={(value) => {
                    setHasCategoryInteraction(true);
                    const nextVal = value === null || value === undefined || value === '' ? null : value;
                    setInquiryType(nextVal);
                    setInquiryProgram(nextVal);
                  }}
                  onBlur={() => markTouched('category')}
                  hasError={shouldShowError('category')}
                  placeholder={isLoadingCategories ? 'Loading...' : 'Select category'}
                  disabled={isLoadingCategories}
                  busy={isLoadingCategories}
                />
                {shouldShowError('category') && requiredErrors.category && (
                  <p className="text-xs text-amber-400">{requiredErrors.category}</p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Inquiry date *</label>
                <Input
                  {...AUTOFILL_PROPS}
                  type="date"
                  value={inquiryDate}
                  onChange={(e) => setInquiryDate(e.target.value)}
                  onBlur={() => markTouched('inquiryDate')}
                  max={todayStr}
                  className={cn(
                    shouldShowError('inquiryDate')
                      ? 'border-red-500 focus-visible:ring-red-500 focus-visible:ring-2 focus-visible:ring-offset-0'
                      : ''
                  )}
                />
                {shouldShowError('inquiryDate') && requiredErrors.inquiryDate && (
                  <p className="text-xs text-amber-400">{requiredErrors.inquiryDate}</p>
                )}
              </div>
              {/* <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Program</label>
                <Input
                  value={inquiryProgram}
                  onChange={(e) => setInquiryProgram(e.target.value)}
                  placeholder="Program / Course"
                />
              </div> */}
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              {/* <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Source</label>
                <Input
                  value={inquirySource}
                  onChange={(e) => setInquirySource(e.target.value)}
                  placeholder="Instagram, Message Ad..."
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Campaign / Tag</label>
                <Input
                  value={inquiryCampaign}
                  onChange={(e) => setInquiryCampaign(e.target.value)}
                  placeholder="Campaign reference"
                />
              </div> */}
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Status *</label>
                <SearchableSelect
                  options={followupInterestOptions.map((item) => ({
                    value: item.name,
                    label: item.name,
                  }))}
                  value={inquiryStatus}
                  onChange={(value) => setInquiryStatus(value || '')}
                  onBlur={() => markTouched('status')}
                  hasError={shouldShowError('status')}
                  placeholder={isLoadingFollowupInterest ? 'Loading...' : 'Select status'}
                  disabled={isLoadingFollowupInterest}
                  busy={isLoadingFollowupInterest}
                />
                {shouldShowError('status') && requiredErrors.status && (
                  <p className="text-xs text-amber-400">{requiredErrors.status}</p>
                )}
              </div>
            </div>
            <div className="grid sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Follow-up date *</label>
                <Input
                  {...AUTOFILL_PROPS}
                  type="date"
                  value={followUpDate}
                  onChange={(e) => setFollowUpDate(e.target.value)}
                  onBlur={() => markTouched('followUpDate')}
                  min={todayStr}
                  className={cn(
                    shouldShowError('followUpDate')
                      ? 'border-red-500 focus-visible:ring-red-500 focus-visible:ring-2 focus-visible:ring-offset-0'
                      : ''
                  )}
                />
                {shouldShowError('followUpDate') && requiredErrors.followUpDate && (
                  <p className="text-xs text-amber-400">{requiredErrors.followUpDate}</p>
                )}
              </div>
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Follow-up time *</label>
                <Input
                  {...AUTOFILL_PROPS}
                  type="time"
                  value={followUpTime}
                  onChange={(e) => setFollowUpTime(e.target.value)}
                  onBlur={() => markTouched('followUpTime')}
                  min={followUpDate === todayStr ? currentTimeStr : undefined}
                  className={cn(
                    shouldShowError('followUpTime')
                      ? 'border-red-500 focus-visible:ring-red-500 focus-visible:ring-2 focus-visible:ring-offset-0'
                      : ''
                  )}
                />
                {shouldShowError('followUpTime') && requiredErrors.followUpTime && (
                  <p className="text-xs text-amber-400">{requiredErrors.followUpTime}</p>
                )}
              </div>
              {/* <div className="space-y-1 flex items-center gap-4">
                <label className="text-xs text-[var(--tg-text-secondary)]">Flags</label>
                <label className="flex items-center gap-1 text-sm text-[var(--tg-text-secondary)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isBlogger}
                      onChange={(e) => setIsBlogger(e.target.checked)}
                    />
                    Blogger
                  </label>
                  <label className="flex items-center gap-1 text-sm text-[var(--tg-text-secondary)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoAssignInquiry}
                      onChange={(e) => setAutoAssignInquiry(e.target.checked)}
                    />
                    Auto assign inquiry
                  </label>
                  <label className="flex items-center gap-1 text-sm text-[var(--tg-text-secondary)] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isFranchisee}
                      onChange={(e) => setIsFranchisee(e.target.checked)}
                    />
                    Franchisee
                  </label>
                </div> */}
            </div>
            {followUpError && (
              <p className="text-xs text-amber-400">{followUpError}</p>
            )}
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">Email</label>
                <Input
                  {...AUTOFILL_PROPS}
                  type="email"
                  value={inquiryEmail}
                  onChange={(e) => setInquiryEmail(e.target.value)}
                  placeholder="user@example.com"
                />
              </div>
              {/* <div className="space-y-1">
                <label className="text-xs text-[var(--tg-text-secondary)]">WhatsApp number</label>
                <Input
                  value={inquiryWhatsApp}
                  onChange={(e) => setInquiryWhatsApp(e.target.value)}
                  placeholder="+1 555 000 0000"
                />
              </div> */}
            </div>
          </div>
        </form>
        <div className="sticky bottom-0 z-10 bg-[var(--tg-surface)] px-6 py-3 border-t border-[var(--tg-border-soft)] flex flex-col gap-2">
          <div className="flex items-center justify-between gap-3 text-[11px] text-[var(--tg-text-muted)]">
            <span>Fill all required fields (*) to create the inquiry.</span>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              className="bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white"
              onClick={handleSubmitInquiry}
              disabled={!canCreateInquiry || isSubmittingInquiry}
              title={
                !canCreateInquiry && !isSubmittingInquiry
                  ? 'Some required fields are missing. Please complete all fields marked with *.'
                  : undefined
              }
            >
              {isSubmittingInquiry ? 'Creating...' : 'Create inquiry'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default CreateInquiryModal;
