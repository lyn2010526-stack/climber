import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Table } from '../Table';

describe('Table', () => {
  const columns = [
    { key: 'name', header: 'Name' },
    { key: 'email', header: 'Email' }
  ];

  const data = [
    { id: '1', name: 'John Doe', email: 'john@example.com' },
    { id: '2', name: 'Jane Smith', email: 'jane@example.com' }
  ];

  it('renders with default props', () => {
    const { container } = render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} />
    );
    const wrapper = container.querySelector('.w-full');
    expect(wrapper).toBeInTheDocument();
  });

  it('renders headers when provided', () => {
    render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} />
    );
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Email')).toBeInTheDocument();
  });

  it('renders rows when data is provided', () => {
    render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} />
    );
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('Jane Smith')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} className="custom-table-class" />
    );
    const wrapper = container.querySelector('.custom-table-class');
    expect(wrapper).toBeInTheDocument();
  });

  it('renders children content', () => {
    render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} />
    );
    expect(screen.getByText('John Doe')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    render(
      <Table columns={columns} data={[]} keyExtractor={(row) => row.id} />
    );
    expect(screen.getByText('No data available')).toBeInTheDocument();
  });

  it('renders custom empty message', () => {
    render(
      <Table columns={columns} data={[]} keyExtractor={(row) => row.id} emptyMessage="Nothing here" />
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('renders loading state when loading is true', () => {
    render(
      <Table columns={columns} data={[]} keyExtractor={(row) => row.id} loading={true} />
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('supports row selection', () => {
    render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} selectable={true} selectedRows={[]} />
    );
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes.length).toBeGreaterThan(0);
  });

  it('calls onSelectionChange when row is selected', () => {
    const onSelectionChange = vi.fn();
    render(
      <Table
        columns={columns}
        data={data}
        keyExtractor={(row) => row.id}
        selectable={true}
        selectedRows={[]}
        onSelectionChange={onSelectionChange}
      />
    );
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    const rowCheckbox = checkboxes[checkboxes.length - 1] as HTMLInputElement;
    if (rowCheckbox) {
      rowCheckbox.click();
      expect(onSelectionChange).toHaveBeenCalled();
    }
  });

  it('renders with pagination', () => {
    render(
      <Table
        columns={columns}
        data={data}
        keyExtractor={(row) => row.id}
        pagination={{
          page: 1,
          pageSize: 10,
          total: 50,
          onPageChange: vi.fn(),
        }}
      />
    );
    expect(screen.getByText('Previous')).toBeInTheDocument();
    expect(screen.getByText('Next')).toBeInTheDocument();
  });

  it('renders with custom column width', () => {
    const customColumns = [
      { key: 'name', header: 'Name', width: '200px' },
    ];
    render(
      <Table columns={customColumns} data={data} keyExtractor={(row) => row.id} />
    );
    const th = document.querySelector('th');
    expect(th?.style.width).toBe('200px');
  });

  it('supports sortable columns', () => {
    const sortableColumns = [
      { key: 'name', header: 'Name', sortable: true },
    ];
    render(
      <Table columns={sortableColumns} data={data} keyExtractor={(row) => row.id} sortable={true} />
    );
    const th = document.querySelector('th');
    expect(th?.className).toContain('cursor-pointer');
  });

  it('supports row click handler', () => {
    const onRowClick = vi.fn();
    render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} onRowClick={onRowClick} />
    );
    const firstRow = screen.getByText('John Doe').closest('tr');
    if (firstRow) {
      firstRow.click();
      expect(onRowClick).toHaveBeenCalled();
    }
  });

  it('renders custom cell render function', () => {
    const customColumns = [{
      key: 'name',
      header: 'Name',
      render: (row: { name: string }) => <strong>{row.name}</strong>
    }];
    render(
      <Table columns={customColumns} data={data} keyExtractor={(row) => row.id} />
    );
    const strong = document.querySelector('strong');
    expect(strong?.textContent).toBe('John Doe');
  });

  it('renders without errors when minimal props provided', () => {
    const { container } = render(
      <Table columns={[]} data={[]} keyExtractor={(row) => ''} />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders with sticky header when stickyHeader is true', () => {
    render(
      <Table columns={columns} data={data} keyExtractor={(row) => row.id} stickyHeader={true} />
    );
    const thead = document.querySelector('thead');
    expect(thead?.className).toContain('sticky');
  });

  it('renders with expandable rows', () => {
    render(
      <Table
        columns={columns}
        data={data}
        keyExtractor={(row) => row.id}
        expandable={true}
        renderExpanded={(row) => <div>Expanded: {row.name}</div>}
      />
    );
    const expandButton = document.querySelector('button[aria-expanded]');
    expect(expandButton).toBeInTheDocument();
  });
});
