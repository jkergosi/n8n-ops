import * as React from 'react';
import { X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from '@/components/ui/command';
import { cn } from '@/lib/utils';

export interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
  className?: string;
}

export function MultiSelect({ options, selected, onChange, placeholder = 'Select...', className }: MultiSelectProps) {
  const [open, setOpen] = React.useState(false);
  const [inputValue, setInputValue] = React.useState('');

  const handleUnselect = (item: string) => {
    onChange(selected.filter((s) => s !== item));
  };

  const handleSelect = (item: string) => {
    if (selected.includes(item)) {
      handleUnselect(item);
    } else {
      onChange([...selected, item]);
    }
  };

  const filteredOptions = React.useMemo(() => {
    if (!inputValue) return options;
    return options.filter((option) =>
      option.toLowerCase().includes(inputValue.toLowerCase())
    );
  }, [options, inputValue]);

  return (
    <div className={cn('relative', className)}>
      <div
        className="flex min-h-9 w-full items-center justify-between rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-within:ring-1 focus-within:ring-ring cursor-text"
        onClick={() => setOpen(true)}
      >
        <div className="flex flex-wrap gap-1">
          {selected.length > 0 ? (
            selected.map((item) => (
              <Badge
                key={item}
                variant="secondary"
                className="mr-1 mb-1"
                onClick={(e) => e.stopPropagation()}
              >
                {item}
                <button
                  className="ml-1 rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleUnselect(item);
                    }
                  }}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                  }}
                  onClick={() => handleUnselect(item)}
                >
                  <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                </button>
              </Badge>
            ))
          ) : (
            <span className="text-muted-foreground">{placeholder}</span>
          )}
        </div>
      </div>

      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute top-full mt-1 w-full z-50 rounded-md border bg-popover p-0 text-popover-foreground shadow-md">
            <Command>
              <CommandInput
                placeholder="Search tags..."
                value={inputValue}
                onValueChange={setInputValue}
              />
              <CommandEmpty>No tags found.</CommandEmpty>
              <CommandGroup className="max-h-64 overflow-auto">
                {filteredOptions.map((option) => {
                  const isSelected = selected.includes(option);
                  return (
                    <CommandItem
                      key={option}
                      onSelect={() => handleSelect(option)}
                      className="cursor-pointer"
                    >
                      <div
                        className={cn(
                          'mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary',
                          isSelected
                            ? 'bg-primary text-primary-foreground'
                            : 'opacity-50 [&_svg]:invisible'
                        )}
                      >
                        <svg
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <polyline points="20 6 9 17 4 12" strokeWidth={2} />
                        </svg>
                      </div>
                      <span>{option}</span>
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            </Command>
          </div>
        </>
      )}
    </div>
  );
}
